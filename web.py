#! /usr/bin/env python

# -*- coding: utf-8 -*-
"""
  CigarBox
  ~~~~~~

  A smokin' fast personal photostream

  :copyright: (c) 2015 by Nathan Hubbard @n8foo.
  :license: Apache, see LICENSE for more details.
"""

import sys
sys.stdout = sys.stderr  # Force stdout to stderr for immediate logging
sys.stderr.flush()
sys.stdout.flush()

from flask import Flask, request, session, g, redirect, url_for, abort, \
  render_template, flash, send_from_directory, jsonify

from flask_security import Security, PeeweeUserDatastore, UserMixin, RoleMixin, \
  login_required, roles_required, current_user

from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix

import math
import secrets
import datetime

from app import app
from util import *
from db import *
from security import get_visible_privacy_levels, can_view_photo, can_edit_photo, \
  can_manage_tags, can_manage_photosets
from peewee import IntegrityError

# Configure Flask to work behind nginx proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

# Setup Flask-Security-Too
user_datastore = PeeweeUserDatastore(db, User, Role, UserRoles)
security = Security(app, user_datastore)

# Register user loader for Flask-Login (Flask-Security uses this)
@security.login_manager.user_loader
def load_user(user_id):
    """Load user by ID from database"""
    try:
        return User.get(User.id == int(user_id))
    except User.DoesNotExist:
        return None

# Ensure database is connected for each request
@app.before_request
def before_request():
    """Connect to database before each request"""
    if db.is_closed():
        db.connect()

@app.teardown_request
def teardown_request(exception):
    """Close database after each request"""
    if not db.is_closed():
        db.close()


# Utility Functions

def get_base_url():
  """Get the base URL dynamically from request"""
  return request.url_root.rstrip('/')

@app.context_processor
def inject_siteurl():
  """Inject SITEURL into all templates"""
  return dict(SITEURL=get_base_url())

def find(lst, key, value):
  for i, dic in enumerate(lst):
    if dic[key] == value:
      return i
  return -1

def get_pagination_data(query, page, per_page):
  """Calculate pagination metadata for a query

  Args:
    query: Peewee SelectQuery object
    page: Current page number (1-indexed)
    per_page: Items per page

  Returns:
    Dictionary with pagination metadata
  """
  total_items = query.count()
  total_pages = math.ceil(total_items / per_page)
  has_prev = page > 1
  has_next = page < total_pages

  return {
    'page': page,
    'per_page': per_page,
    'total_items': total_items,
    'total_pages': total_pages,
    'has_prev': has_prev,
    'has_next': has_next,
    'prev_page': page - 1 if has_prev else None,
    'next_page': page + 1 if has_next else None
  }

# URL Routing

@app.errorhandler(404)
def page_not_found(error):
  return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(error):
  return render_template('500.html'), 500


@app.route('/', defaults={'page': 1})
@app.route('/photostream', defaults={'page': 1})
@app.route('/photostream/page/<int:page>')
def photostream(page):
  """the list of the most recently added pictures"""
  baseurl = '%s/photostream' % (get_base_url())
  # Filter by privacy level based on current user (treat NULL as public)
  visible_levels = get_visible_privacy_levels(current_user)
  photos_query = Photo.select().where(
    (Photo.privacy.is_null()) | (Photo.privacy.in_(visible_levels))
  ).order_by(Photo.id.desc())

  # Get pagination metadata
  pagination = get_pagination_data(photos_query, page, app.config['PER_PAGE'])

  # Get paginated results
  photos = photos_query.paginate(page, app.config['PER_PAGE'])
  for photo in photos:
    (sha1Path,filename) = getSha1Path(photo.sha1)
    photo.uri = sha1Path + '/' + filename

  return render_template('photostream.html', photos=photos, pagination=pagination, baseurl=baseurl)

@app.route('/photos/<int:photo_id>')
def show_photo(photo_id):
  """a single photo"""
  photo = Photo.select().where(Photo.id == photo_id).get()
  # Check if user has permission to view this photo
  if not can_view_photo(current_user, photo):
    abort(403)
  (sha1Path,filename) = getSha1Path(photo.sha1)
  photo.uri = sha1Path + '/' + filename
  tags = Tag.select().join(PhotoTag).where(PhotoTag.photo == photo_id)

  # Get photosets this photo belongs to
  photo_photosets = (PhotoPhotoset.select()
                    .join(Photoset)
                    .where(PhotoPhotoset.photo == photo))

  # Check if user can edit this photo
  can_edit = can_edit_photo(current_user, photo)

  return render_template('photos.html', photo=photo, tags=tags,
                        photo_photosets=photo_photosets, can_edit=can_edit)


@app.route('/photos/<int:photo_id>/update', methods=['POST'])
@login_required
def update_photo_inline(photo_id):
  """Update photo metadata inline"""
  photo = Photo.select().where(Photo.id == photo_id).get()

  # Check permission
  if not can_edit_photo(current_user, photo):
    abort(403)

  action = request.form.get('action')

  if action == 'privacy':
    # Update privacy
    privacy = request.form.get('privacy')
    if privacy:
      photo.privacy = int(privacy) if privacy != 'null' else None
      photo.save()
      flash('Privacy updated')

  elif action == 'tags':
    # Update tags
    tags_input = request.form.get('tags', '')

    # Remove existing tags
    PhotoTag.delete().where(PhotoTag.photo == photo_id).execute()

    # Add new tags
    if tags_input:
      tag_names = [t.strip() for t in tags_input.split(',') if t.strip()]
      for tag_name in tag_names:
        tag, created = Tag.get_or_create(name=tag_name)
        PhotoTag.create(photo=photo, tag=tag)

    flash('Tags updated')

  return redirect(url_for('show_photo', photo_id=photo_id))

@app.route('/photos/<int:photo_id>/original')
@login_required
def show_original_photo(photo_id):
  """Get signed S3 URL for original photo file"""
  photo = Photo.select().where(Photo.id == photo_id).get()

  # Check permission to view this photo
  if not can_view_photo(current_user, photo):
    abort(403)

  (sha1Path,filename) = getSha1Path(photo.sha1)
  S3Key = '/'+sha1Path+'/'+filename+'.'+photo.filetype
  originalURL = aws.getPrivateURL(app.config,S3Key)
  return redirect(originalURL)


@app.route('/photos/bulk-edit', methods=['GET', 'POST'], defaults={'page': 1})
@app.route('/photos/bulk-edit/page/<int:page>', methods=['GET', 'POST'])
@login_required
def bulk_edit_photos(page):
  """Bulk edit multiple photos at once"""

  if request.method == 'POST':
    # Handle bulk updates
    photo_ids = request.form.get('photo_ids', '').split(',')
    action = request.form.get('action')
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    # Debug logging
    print(f"[BULK EDIT] Action: {action}, Photo IDs count: {len([p for p in photo_ids if p])}, AJAX: {is_ajax}")

    message = ''
    success = True

    try:
      if action == 'bulk_tags_add':
        # Add tags to all photos
        tags_input = request.form.get('bulk_tags', '')
        if tags_input:
          tag_names = [t.strip() for t in tags_input.split(',') if t.strip()]
          count = 0
          for photo_id in photo_ids:
            if not photo_id:
              continue
            photo = Photo.select().where(Photo.id == int(photo_id)).first()
            if photo and can_edit_photo(current_user, photo):
              for tag_name in tag_names:
                tag, created = Tag.get_or_create(name=tag_name)
                PhotoTag.get_or_create(photo=photo, tag=tag)
              count += 1
          message = f'Added tags to {count} photos'
        else:
          message = 'No tags provided'
          success = False

      elif action == 'bulk_privacy':
        # Set privacy for all photos
        privacy = request.form.get('bulk_privacy')
        if privacy:
          count = 0
          for photo_id in photo_ids:
            if not photo_id:
              continue
            photo = Photo.select().where(Photo.id == int(photo_id)).first()
            if photo and can_edit_photo(current_user, photo):
              photo.privacy = int(privacy) if privacy != 'null' else None
              photo.save()
              count += 1
          message = f'Updated privacy for {count} photo{"s" if count != 1 else ""}'
        else:
          message = 'No privacy level selected'
          success = False

      elif action == 'bulk_photoset':
        # Add all photos to photoset
        photoset_id = request.form.get('bulk_photoset')
        if photoset_id:
          photoset = Photoset.select().where(Photoset.id == int(photoset_id)).first()
          if photoset:
            count = 0
            for photo_id in photo_ids:
              if not photo_id:
                continue
              photo = Photo.select().where(Photo.id == int(photo_id)).first()
              if photo and can_edit_photo(current_user, photo):
                PhotoPhotoset.get_or_create(photo=photo, photoset=photoset)
                count += 1
            message = f'Added {count} photos to photoset "{photoset.title}"'
          else:
            message = 'Photoset not found'
            success = False
        else:
          message = 'No photoset selected'
          success = False

      elif action == 'individual_privacy':
        # Update individual photo privacy levels
        count = 0
        for photo_id in photo_ids:
          if not photo_id:
            continue
          privacy_key = f'privacy_{photo_id}'
          if privacy_key in request.form:
            photo = Photo.select().where(Photo.id == int(photo_id)).first()
            if photo and can_edit_photo(current_user, photo):
              privacy = request.form.get(privacy_key)
              photo.privacy = int(privacy) if privacy else None
              photo.save()
              count += 1
        message = f'Updated privacy for {count} photo{"s" if count != 1 else ""}'

      elif action == 'individual_tags':
        # Update individual photo tags
        count = 0
        for photo_id in photo_ids:
          if not photo_id:
            continue
          tags_key = f'tags_{photo_id}'
          if tags_key in request.form:
            photo = Photo.select().where(Photo.id == int(photo_id)).first()
            if photo and can_edit_photo(current_user, photo):
              # Remove existing tags
              PhotoTag.delete().where(PhotoTag.photo == photo).execute()
              # Add new tags
              tags_input = request.form.get(tags_key, '')
              if tags_input:
                tag_names = [t.strip() for t in tags_input.split(',') if t.strip()]
                for tag_name in tag_names:
                  tag, created = Tag.get_or_create(name=tag_name)
                  PhotoTag.create(photo=photo, tag=tag)
              count += 1
        message = f'Updated tags for {count} photo{"s" if count != 1 else ""}'

      elif action == 'individual_both':
        # Update both privacy and tags for photos
        count = 0
        for photo_id in photo_ids:
          if not photo_id:
            continue
          photo = Photo.select().where(Photo.id == int(photo_id)).first()
          if photo and can_edit_photo(current_user, photo):
            # Update privacy
            privacy_key = f'privacy_{photo_id}'
            if privacy_key in request.form:
              privacy = request.form.get(privacy_key)
              photo.privacy = int(privacy) if privacy else None
              photo.save()

            # Update tags
            tags_key = f'tags_{photo_id}'
            if tags_key in request.form:
              PhotoTag.delete().where(PhotoTag.photo == photo).execute()
              tags_input = request.form.get(tags_key, '')
              if tags_input:
                tag_names = [t.strip() for t in tags_input.split(',') if t.strip()]
                for tag_name in tag_names:
                  tag, created = Tag.get_or_create(name=tag_name)
                  PhotoTag.create(photo=photo, tag=tag)
            count += 1
        message = f'Updated {count} photo{"s" if count != 1 else ""}'

    except Exception as e:
      message = f'Error: {str(e)}'
      success = False

    # Return JSON for AJAX requests
    if is_ajax:
      return jsonify({'success': success, 'message': message})

    # Flash message and redirect for normal requests
    flash(message)
    return redirect(url_for('bulk_edit_photos', ids=','.join(photo_ids)))

  # GET request - show bulk edit interface
  try:
    ids = request.args.get('ids', '')
    if not ids:
      flash('No photos selected')
      return redirect(url_for('photostream'))

    photo_ids = [int(id) for id in ids.split(',') if id.strip().isdigit()]
    logger.info(f'Bulk edit: {len(photo_ids)} photo IDs requested')

    # Load photos
    photos = Photo.select().where(Photo.id.in_(photo_ids)).order_by(Photo.ts.desc())

    # Check permissions and prepare photo data
    editable_photos = []
    for photo in photos:
      if can_view_photo(current_user, photo):
        (sha1Path, filename) = getSha1Path(photo.sha1)
        photo.uri = sha1Path + '/' + filename
        photo.can_edit = can_edit_photo(current_user, photo)

        # Get existing tags
        photo.tag_list = list(Tag.select().join(PhotoTag).where(PhotoTag.photo == photo))

        editable_photos.append(photo)

    # Get grouping preference (sanitize to prevent path injection)
    group_by = request.args.get('group_by', 'upload_date')
    # Strip any path components that got appended accidentally
    if '/' in group_by:
      group_by = group_by.split('/')[0]
    # Validate it's a known value
    if group_by not in ['upload_date', 'date_taken']:
      group_by = 'upload_date'

    # Group photos by chosen method
    from collections import defaultdict
    grouped_photos = defaultdict(list)

    for photo in editable_photos:
      if group_by == 'date_taken':
        # Try to use date taken from EXIF
        if photo.datetaken:
          group_key = photo.datetaken.date()
          group_label = photo.datetaken.strftime('%Y-%m-%d')
        else:
          # Fall back to file date from ImportMeta
          import_meta = ImportMeta.select().where(ImportMeta.photo == photo.id).first()
          if import_meta and import_meta.filedate:
            # Parse filedate if it's a string
            if isinstance(import_meta.filedate, str):
              try:
                filedate_obj = datetime.datetime.strptime(import_meta.filedate, '%Y-%m-%d %H:%M:%S')
                group_key = filedate_obj.date()
                group_label = filedate_obj.strftime('%Y-%m-%d') + ' (file date)'
              except ValueError:
                # Couldn't parse filedate
                group_key = datetime.date(1970, 1, 1)
                group_label = 'Unknown Date'
            else:
              group_key = import_meta.filedate.date()
              group_label = import_meta.filedate.strftime('%Y-%m-%d') + ' (file date)'
          else:
            # No date info available
            group_key = datetime.date(1970, 1, 1)  # Sort to bottom
            group_label = 'Unknown Date'
      else:
        # Group by upload date (day only)
        group_key = photo.ts.date()
        group_label = photo.ts.strftime('%Y-%m-%d')

      grouped_photos[(group_key, group_label)].append(photo)

    # Convert to sorted list of ((date, label), photos) tuples
    photo_groups = sorted(grouped_photos.items(), key=lambda x: x[0][0], reverse=True)

    # Get all photosets for dropdown
    photosets = Photoset.select().order_by(Photoset.title)

    # Paginate the editable_photos list
    per_page = 100
    total_photos = len(editable_photos)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_photos = editable_photos[start_idx:end_idx]

    # Re-group only the paginated photos
    grouped_photos_paginated = defaultdict(list)
    for photo in paginated_photos:
      if group_by == 'date_taken':
        if photo.datetaken:
          group_key = photo.datetaken.date()
          group_label = photo.datetaken.strftime('%Y-%m-%d')
        else:
          import_meta = ImportMeta.select().where(ImportMeta.photo == photo.id).first()
          if import_meta and import_meta.filedate:
            if isinstance(import_meta.filedate, str):
              try:
                filedate_obj = datetime.datetime.strptime(import_meta.filedate, '%Y-%m-%d %H:%M:%S')
                group_key = filedate_obj.date()
                group_label = filedate_obj.strftime('%Y-%m-%d') + ' (file date)'
              except ValueError:
                group_key = datetime.date(1970, 1, 1)
                group_label = 'Unknown Date'
            else:
              group_key = import_meta.filedate.date()
              group_label = import_meta.filedate.strftime('%Y-%m-%d') + ' (file date)'
          else:
            group_key = datetime.date(1970, 1, 1)
            group_label = 'Unknown Date'
      else:
        group_key = photo.ts.date()
        group_label = photo.ts.strftime('%Y-%m-%d')

      grouped_photos_paginated[(group_key, group_label)].append(photo)

    photo_groups_paginated = sorted(grouped_photos_paginated.items(), key=lambda x: x[0][0], reverse=True)

    # Pagination metadata
    total_pages = (total_photos + per_page - 1) // per_page
    # Build pagination URLs correctly (query params separate from path)
    query_params = f'ids={ids}&group_by={group_by}'
    pagination = {
      'page': page,
      'per_page': per_page,
      'total': total_photos,
      'total_pages': total_pages,
      'has_prev': page > 1,
      'has_next': page < total_pages,
      'prev_num': page - 1 if page > 1 else None,
      'next_num': page + 1 if page < total_pages else None,
      'prev_url': f'{get_base_url()}/photos/bulk-edit/page/{page-1}?{query_params}' if page > 1 else None,
      'next_url': f'{get_base_url()}/photos/bulk-edit/page/{page+1}?{query_params}' if page < total_pages else None,
    }
    baseurl = f'{get_base_url()}/photos/bulk-edit?{query_params}'

    # Get all existing tags for autocomplete
    all_tags = Tag.select().order_by(Tag.name)

    return render_template('bulk_edit.html',
                          photo_groups=photo_groups_paginated,
                          photo_ids=','.join(str(id) for id in photo_ids),
                          total_photos=total_photos,
                          photosets=photosets,
                          all_tags=all_tags,
                          group_by=group_by,
                          pagination=pagination,
                          baseurl=baseurl)
  except Exception as e:
    logger.error(f'Bulk edit error: {e}', exc_info=True)
    flash(f'Error loading bulk edit page')
    return redirect(url_for('photostream'))

@app.route('/tags')
def show_tags():
  # Filter tags to only show counts for photos user can see (treat NULL as public)
  visible_levels = get_visible_privacy_levels(current_user)
  tags = (Tag
         .select(Tag, fn.Count(Photo.id).alias('count'))
         .join(PhotoTag)
         .join(Photo)
         .where((Photo.privacy.is_null()) | (Photo.privacy.in_(visible_levels)))
         .group_by(Tag))
  return render_template('tag_cloud.html', tags=tags)

@app.route('/tags/<string:tag>', defaults={'page': 1})
@app.route('/tags/<string:tag>/page/<int:page>')
def show_taged_photos(tag,page):
  baseurl = '%s/tags/%s' % (get_base_url(),tag)
  visible_levels = get_visible_privacy_levels(current_user)
  photos_query = (Photo.select()
                  .join(PhotoTag)
                  .join(Tag)
                  .where((Tag.name == tag) & ((Photo.privacy.is_null()) | (Photo.privacy.in_(visible_levels))))
                  .order_by(Photo.id.desc()))

  # Get pagination metadata
  pagination = get_pagination_data(photos_query, page, app.config['PER_PAGE'])

  # Get paginated results
  photos = photos_query.paginate(page, app.config['PER_PAGE'])
  for photo in photos:
    (sha1Path,filename) = getSha1Path(photo.sha1)
    photo.uri = sha1Path + '/' + filename

  # Get tag object
  tag_obj = Tag.select().where(Tag.name == tag).first()
  if not tag_obj:
    abort(404)

  # Get total photo count for this tag
  photo_count = photos_query.count()
  can_manage = can_manage_tags(current_user)

  # Get all photo IDs for bulk edit link (not just current page)
  all_photo_ids = [str(p.id) for p in photos_query]
  photo_ids_str = ','.join(all_photo_ids)

  return render_template('tag.html', photos=photos, tag=tag_obj,
                        photo_count=photo_count, pagination=pagination,
                        baseurl=baseurl, can_manage=can_manage,
                        photo_ids=photo_ids_str)


@app.route('/tags/<string:tag>/rename', methods=['POST'])
@login_required
def rename_tag_inline(tag):
  """Rename a tag"""
  if not can_manage_tags(current_user):
    abort(403)

  tag_obj = Tag.select().where(Tag.name == tag).first()
  if not tag_obj:
    abort(404)

  new_name = request.form.get('new_name', '').strip()
  if not new_name:
    flash('Tag name cannot be empty')
    return redirect(url_for('show_taged_photos', tag=tag, page=1))

  if new_name == tag:
    flash('Tag name unchanged')
    return redirect(url_for('show_taged_photos', tag=tag, page=1))

  # Check if target tag already exists
  existing = Tag.select().where(Tag.name == new_name).first()
  if existing:
    flash(f'Tag "{new_name}" already exists. Use merge instead.')
    return redirect(url_for('show_taged_photos', tag=tag, page=1))

  # Rename the tag
  tag_obj.name = new_name
  tag_obj.save()

  flash(f'Tag renamed to "{new_name}"')
  return redirect(url_for('show_taged_photos', tag=new_name, page=1))


@app.route('/tags/<string:tag>/merge', methods=['POST'])
@login_required
def merge_tag_inline(tag):
  """Merge one tag into another"""
  if not can_manage_tags(current_user):
    abort(403)

  source_tag = Tag.select().where(Tag.name == tag).first()
  if not source_tag:
    abort(404)

  target_tag_name = request.form.get('target_tag', '').strip()
  if not target_tag_name:
    flash('Target tag name required')
    return redirect(url_for('show_taged_photos', tag=tag, page=1))

  # Get or create target tag
  target_tag, created = Tag.get_or_create(name=target_tag_name)

  if target_tag.id == source_tag.id:
    flash('Cannot merge tag into itself')
    return redirect(url_for('show_taged_photos', tag=tag, page=1))

  # Move all photos from source tag to target tag
  photo_tags = PhotoTag.select().where(PhotoTag.tag == source_tag)
  count = 0
  for pt in photo_tags:
    # Check if photo already has target tag
    existing = PhotoTag.select().where(
      (PhotoTag.photo == pt.photo) & (PhotoTag.tag == target_tag)
    ).first()

    if not existing:
      # Create new relationship with target tag
      PhotoTag.create(photo=pt.photo, tag=target_tag)

    # Delete old relationship
    pt.delete_instance()
    count += 1

  # Delete source tag
  source_tag.delete_instance()

  flash(f'Merged "{tag}" into "{target_tag_name}" ({count} photos moved)')
  return redirect(url_for('show_taged_photos', tag=target_tag_name, page=1))

@app.route('/date/<string:date>', defaults={'page': 1})
@app.route('/date/<string:date>/page/<int:page>')
def show_date_photos(date,page):
  baseurl = '%s/date/%s' % (get_base_url(),date)
  visible_levels = get_visible_privacy_levels(current_user)
  photos_query = (Photo.select()
                  .where((Photo.datetaken.startswith(date)) & ((Photo.privacy.is_null()) | (Photo.privacy.in_(visible_levels))))
                  .order_by(Photo.datetaken.desc()))

  # Get pagination metadata
  pagination = get_pagination_data(photos_query, page, app.config['PER_PAGE'])

  # Get paginated results
  photos = photos_query.paginate(page, app.config['PER_PAGE'])
  for photo in photos:
    (sha1Path,filename) = getSha1Path(photo.sha1)
    photo.uri = sha1Path + '/' + filename

  # Get photo count and IDs for bulk edit
  photo_count = photos_query.count()
  all_photo_ids = [str(p.id) for p in photos_query]
  photo_ids_str = ','.join(all_photo_ids)

  return render_template('photostream.html', photos=photos, pagination=pagination,
                        baseurl=baseurl, page_title=f'Photos from {date}',
                        photo_count=photo_count, photo_ids=photo_ids_str)

@app.route('/tags/<string:tag>/delete')
@login_required
def delete_tag(tag):
  # Check permission
  if not can_manage_tags(current_user):
    abort(403)
  # get tag id since delete() doesn't support joins
  deleteTag = Tag.select().where(Tag.name == tag)
  deleteTag = deleteTag.get()
  # delete relationship to photos
  deleteTags = PhotoTag.delete().where(PhotoTag.tag == deleteTag.id)
  deleteTags.execute()
  # delete tag from db
  deletedTag = Tag.delete().where(Tag.name == tag)
  deletedTag.execute()
  flash('Tag deleted')
  return redirect(url_for('show_tags'))

@app.route('/photos/<int:photo_id>/delete')
@login_required
def delete_photo(photo_id):
  # Check permission
  photo = Photo.select().where(Photo.id == photo_id).get()
  if not can_edit_photo(current_user, photo):
    abort(403)
  # delete photo from S3 (not working)
  #(sha1Path,filename) = getSha1Path(photo.sha1)
  #S3key='/%s/%s.%s' % (sha1Path,filename,photo.filetype)
  #aws.deleteFromS3(S3key,app.config)
  # delete photo from db
  deletedPhoto = Photo.delete().where(Photo.id == photo_id)
  deletedPhoto.execute()
  flash('Photo deleted')
  return redirect(url_for('photostream'))

@app.route('/photosets', defaults={'page': 1})
@app.route('/photosets/page/<int:page>')
def show_photosets(page):
  thumbCount = 2
  baseurl = '%s/photosets' % (get_base_url())
  visible_levels = get_visible_privacy_levels(current_user)
  photosets_query = Photoset.select().order_by(Photoset.ts.desc())

  # Get pagination metadata
  pagination = get_pagination_data(photosets_query, page, app.config['PER_PAGE'])

  # Get paginated results
  photosets = photosets_query.paginate(page, app.config['PER_PAGE'])
  for photoset in photosets:
    # Filter thumbnails by privacy (treat NULL as public)
    thumbs = Photo.select().join(PhotoPhotoset).join(Photoset)
    thumbs = thumbs.where((Photoset.id == photoset.id) & ((Photo.privacy.is_null()) | (Photo.privacy.in_(visible_levels))))
    thumbs = thumbs.limit(thumbCount)
    thumbs = thumbs.order_by(Photo.datetaken.asc())
    for thumb in thumbs:
      (sha1Path, filename) = getSha1Path(thumb.sha1)
      thumb.uri = '%s/%s_t.jpg' % (sha1Path, filename)
    photoset.thumbs = thumbs

  return render_template('photosets.html', photosets=photosets, pagination=pagination, baseurl=baseurl)

@app.route('/photosets/<int:photoset_id>', defaults={'page': 1})
@app.route('/photosets/<int:photoset_id>/page/<int:page>')
def show_photoset(photoset_id,page):
  baseurl = '%s/photosets/%s' % (get_base_url(), photoset_id)
  visible_levels = get_visible_privacy_levels(current_user)
  photos_query = (Photo.select()
                  .join(PhotoPhotoset)
                  .join(Photoset)
                  .where((Photoset.id == photoset_id) & ((Photo.privacy.is_null()) | (Photo.privacy.in_(visible_levels))))
                  .order_by(Photo.datetaken.asc()))

  # Get pagination metadata
  pagination = get_pagination_data(photos_query, page, app.config['PER_PAGE'])

  # Get paginated results
  photos = photos_query.paginate(page, app.config['PER_PAGE'])
  for photo in photos:
    (sha1Path,filename) = getSha1Path(photo.sha1)
    photo.uri = sha1Path + '/' + filename

  photoset = Photoset.select().where(Photoset.id == photoset_id).get()
  can_manage = can_manage_photosets(current_user)

  # Get all photo IDs for bulk edit link (not just current page)
  all_photo_ids = [str(p.id) for p in photos_query]
  photo_ids_str = ','.join(all_photo_ids)

  return render_template('photoset.html', photos=photos, photoset=photoset,
                        pagination=pagination, baseurl=baseurl, can_manage=can_manage,
                        photo_ids=photo_ids_str)


@app.route('/photosets/<int:photoset_id>/update', methods=['POST'])
@login_required
def update_photoset_inline(photoset_id):
  """Update photoset metadata inline"""
  if not can_manage_photosets(current_user):
    abort(403)

  photoset = Photoset.select().where(Photoset.id == photoset_id).get()
  photoset.title = request.form.get('title', photoset.title)
  photoset.description = request.form.get('description', '')
  photoset.save()

  flash('Photoset updated')
  return redirect(url_for('show_photoset', photoset_id=photoset_id, page=1))


@app.route('/photosets/<int:photoset_id>/remove-photos', methods=['POST'])
@login_required
def remove_photos_from_photoset(photoset_id):
  """Remove selected photos from photoset"""
  if not can_manage_photosets(current_user):
    abort(403)

  photo_ids = request.form.getlist('photo_ids')
  if photo_ids:
    PhotoPhotoset.delete().where(
      (PhotoPhotoset.photoset == photoset_id) &
      (PhotoPhotoset.photo.in_(photo_ids))
    ).execute()
    flash(f'Removed {len(photo_ids)} photo(s) from photoset')

  return redirect(url_for('show_photoset', photoset_id=photoset_id, page=1))


@app.route('/photosets/<int:photoset_id>/delete')
@login_required
def delete_photoset(photoset_id):
  # Check permission
  if not can_manage_photosets(current_user):
    abort(403)
  # clean up relationships to soon-to-be deleted photoset
  #PhotoPhotoset.delete().where(PhotoPhotoset.photoset == photoset_id).execute
  # delete photoset
  photoset = Photoset.get(Photoset.id == photoset_id)
  photoset.delete_instance(recursive=True)
  flash('Photoset deleted')

  # Get page number from referrer or query string to return to same page
  page = request.args.get('page', 1, type=int)
  return redirect(url_for('admin_photosets', page=page))

@app.route('/photosets/<int:photoset_id>/deletephotos')
@login_required
def delete_photoset_photos(photoset_id):
  # Check permission
  if not can_manage_photosets(current_user):
    abort(403)
  # delete all photos and the photoset
  photos = Photo.select().join(PhotoPhotoset).join(Photoset)
  photos = photos.where(Photoset.id == photoset_id)
  for photo in photos:
    deletedPhoto = Photo.delete().where(Photo.id == photo.id)
    deletedPhoto.execute()
  # delete photoset
  photoset = Photoset.get(Photoset.id == photoset_id)
  photoset.delete_instance(recursive=True)
  flash('Photoset and all photos deleted')
  return redirect(url_for('photostream'))

@app.route('/sha1/<string:sha1>')
def show_photo_from_sha1(sha1):
  """a single photo"""
  try:
    photo = Photo.select().where(Photo.sha1 == sha1).get()
  except Exception as e:
    page_not_found('no matching sha1 found')
  else:
    (sha1Path,filename) = getSha1Path(photo.sha1)
    photo.uri = sha1Path + '/' + filename
    tags = Tag.select().join(PhotoTag).where(PhotoTag.photo == photo.id)
    return render_template('photos.html', photo=photo, tags=tags)

@app.route('/add', methods=['POST'])
@login_required
def add_photo():
  flash('New photo was successfully posted')
  return redirect(url_for('show_photos'))


@app.route('/about')
def about():
  return render_template('about.html')

@app.route('/debug/user')
@login_required
def debug_user():
  """Debug endpoint to check current user's permissions"""
  user_roles = []
  if current_user.is_authenticated:
    for role in current_user.roles:
      user_roles.append(role.name)

  debug_info = {
    'authenticated': current_user.is_authenticated,
    'email': current_user.email if current_user.is_authenticated else None,
    'id': current_user.id if current_user.is_authenticated else None,
    'permission_level': current_user.permission_level if current_user.is_authenticated else None,
    'roles': user_roles,
    'has_admin_role': current_user.has_role('admin') if current_user.is_authenticated else False,
  }

  return f"<pre>{debug_info}</pre>"

# upload

# For a given file, return whether it's an allowed type or not
def allowed_file(filename):
  return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/upload', methods=['POST'])
@login_required
def upload():
  # Get the name of the uploaded files
  uploaded_files = request.files.getlist("file[]")
  filenames = []
  for file in uploaded_files:
    # Check if the file is one of the allowed types/extensions
    if file and allowed_file(file.filename):
      # Make the filename safe, remove unsupported chars
      filename = secure_filename(file.filename)
      # Move the file form the temporal folder to the upload
      # folder we setup
      file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
      # Save the filename into a list, we'll use it later
      filenames.append(filename)
      # Redirect the user to the uploaded_file route, which
      # will basicaly show on the browser the uploaded file
  # Load an html page with a link to each uploaded file
  return render_template('uploaded.html', filenames=filenames)

@app.route('/upload',methods=['GET'])
def upload_form():
  return render_template('upload.html')

# This route is expecting a parameter containing the name
# of a file. Then it will locate that file on the upload
# directory and show it on the browser, so if the user uploads
# an image, that image is going to be show after the upload
@app.route('/uploads/<filename>')
def uploaded_file(filename):
  return send_from_directory(app.config['UPLOAD_FOLDER'],filename)


# Admin routes
@app.route('/admin')
@roles_required('admin')
def admin_dashboard():
  """Admin dashboard overview with statistics"""
  stats = {
    'total_photos': Photo.select().count(),
    'total_tags': Tag.select().count(),
    'total_photosets': Photoset.select().count(),
    'total_users': User.select().count(),
    'recent_photos': Photo.select().order_by(Photo.ts.desc()).limit(10),
    'privacy_breakdown': {
      'public': Photo.select().where((Photo.privacy == 0) | (Photo.privacy.is_null())).count(),
      'friends': Photo.select().where(Photo.privacy == 1).count(),
      'family': Photo.select().where(Photo.privacy == 2).count(),
      'private': Photo.select().where(Photo.privacy == 3).count(),
    }
  }

  # Add URI to recent photos
  for photo in stats['recent_photos']:
    (sha1Path, filename) = getSha1Path(photo.sha1)
    photo.uri = sha1Path + '/' + filename

  return render_template('admin/dashboard.html', stats=stats)


@app.route('/admin/photos', defaults={'page': 1})
@app.route('/admin/photos/page/<int:page>')
@roles_required('admin')
def admin_photos(page):
  """Admin photo management interface"""
  baseurl = '%s/admin/photos' % (get_base_url())

  # Optional search filter
  search = request.args.get('search', '')

  if search:
    # Search by ID or SHA1
    photos_query = Photo.select().where(
      (Photo.id == search) | (Photo.sha1.contains(search))
    ).order_by(Photo.id.desc())
  else:
    photos_query = Photo.select().order_by(Photo.id.desc())

  # Get pagination metadata
  pagination = get_pagination_data(photos_query, page, app.config['PER_PAGE'])

  # Get paginated results
  photos = photos_query.paginate(page, app.config['PER_PAGE'])
  for photo in photos:
    (sha1Path, filename) = getSha1Path(photo.sha1)
    photo.uri = sha1Path + '/' + filename
    # Get tags for each photo
    photo.tag_list = list(Tag.select().join(PhotoTag).where(PhotoTag.photo == photo.id))

  return render_template('admin/photos.html', photos=photos, pagination=pagination,
                        baseurl=baseurl, search=search)


@app.route('/admin/photos/<int:photo_id>/edit', methods=['GET', 'POST'])
@roles_required('admin')
def admin_edit_photo(photo_id):
  """Edit photo metadata"""
  photo = Photo.select().where(Photo.id == photo_id).get()

  if request.method == 'POST':
    # Update photo metadata
    privacy = request.form.get('privacy')
    if privacy:
      photo.privacy = int(privacy) if privacy != 'null' else None

    datetaken = request.form.get('datetaken')
    if datetaken:
      photo.datetaken = datetaken

    photo.save()

    # Handle tags
    tags_input = request.form.get('tags', '')
    if tags_input:
      # Remove existing tags
      PhotoTag.delete().where(PhotoTag.photo == photo_id).execute()

      # Add new tags
      tag_names = [t.strip() for t in tags_input.split(',') if t.strip()]
      for tag_name in tag_names:
        tag, created = Tag.get_or_create(name=tag_name)
        PhotoTag.create(photo=photo, tag=tag)

    flash('Photo updated successfully')
    return redirect(url_for('admin_photos'))

  # GET request - show edit form
  (sha1Path, filename) = getSha1Path(photo.sha1)
  photo.uri = sha1Path + '/' + filename
  tags = Tag.select().join(PhotoTag).where(PhotoTag.photo == photo_id)
  tag_names = ','.join([tag.name for tag in tags])

  return render_template('admin/edit_photo.html', photo=photo, tag_names=tag_names)


@app.route('/admin/tags')
@app.route('/admin/tags/page/<int:page>')
@roles_required('admin')
def admin_tags(page=1):
  """Admin tag management interface"""
  per_page = app.config['PER_PAGE']

  # Optional search filter
  search = request.args.get('search', '')

  if search:
    # Search by tag name
    tags_query = (Tag
           .select(Tag, fn.Count(Photo.id).alias('count'))
           .join(PhotoTag, JOIN.LEFT_OUTER)
           .join(Photo, JOIN.LEFT_OUTER)
           .where(Tag.name.contains(search))
           .group_by(Tag)
           .order_by(fn.Count(Photo.id).desc()))
  else:
    tags_query = (Tag
           .select(Tag, fn.Count(Photo.id).alias('count'))
           .join(PhotoTag, JOIN.LEFT_OUTER)
           .join(Photo, JOIN.LEFT_OUTER)
           .group_by(Tag)
           .order_by(fn.Count(Photo.id).desc()))

  # Calculate pagination
  pagination = get_pagination_data(tags_query, page, per_page)

  # Get paginated results
  tags = tags_query.paginate(page, per_page)

  return render_template('admin/tags.html',
                        tags=tags,
                        pagination=pagination,
                        baseurl=get_base_url(),
                        search=search)


@app.route('/admin/tags/<int:tag_id>/edit', methods=['GET', 'POST'])
@roles_required('admin')
def admin_edit_tag(tag_id):
  """Rename a tag"""
  tag = Tag.select().where(Tag.id == tag_id).get()

  if request.method == 'POST':
    new_name = request.form.get('name')
    if new_name and new_name != tag.name:
      # Check if tag with new name already exists
      existing = Tag.select().where(Tag.name == new_name).first()
      if existing:
        flash('Tag with that name already exists')
      else:
        tag.name = new_name
        tag.save()
        flash('Tag renamed successfully')
        return redirect(url_for('admin_tags'))

  return render_template('admin/edit_tag.html', tag=tag)


@app.route('/admin/tags/<int:tag_id>/merge', methods=['POST'])
@roles_required('admin')
def admin_merge_tag(tag_id):
  """Merge one tag into another"""
  source_tag = Tag.select().where(Tag.id == tag_id).get()
  target_tag_name = request.form.get('target_tag')

  if not target_tag_name:
    flash('Target tag name required')
    return redirect(url_for('admin_tags'))

  # Get or create target tag
  target_tag, created = Tag.get_or_create(name=target_tag_name)

  if target_tag.id == source_tag.id:
    flash('Cannot merge tag into itself')
    return redirect(url_for('admin_tags'))

  # Move all photos from source tag to target tag
  photo_tags = PhotoTag.select().where(PhotoTag.tag == source_tag)
  for pt in photo_tags:
    # Check if photo already has target tag
    existing = PhotoTag.select().where(
      (PhotoTag.photo == pt.photo) & (PhotoTag.tag == target_tag)
    ).first()

    if not existing:
      # Create new relationship with target tag
      PhotoTag.create(photo=pt.photo, tag=target_tag)

    # Delete old relationship
    pt.delete_instance()

  # Delete source tag
  source_tag.delete_instance()

  flash(f'Tag "{source_tag.name}" merged into "{target_tag.name}"')
  return redirect(url_for('admin_tags'))


@app.route('/admin/photosets')
@app.route('/admin/photosets/page/<int:page>')
@roles_required('admin')
def admin_photosets(page=1):
  """Admin photoset management interface"""
  per_page = app.config['PER_PAGE']

  # Optional search filter
  search = request.args.get('search', '')

  if search:
    # Search by photoset title or description
    photosets_query = (Photoset.select()
                      .where((Photoset.title.contains(search)) |
                            (Photoset.description.contains(search)))
                      .order_by(Photoset.ts.desc()))
  else:
    photosets_query = Photoset.select().order_by(Photoset.ts.desc())

  # Calculate pagination
  pagination = get_pagination_data(photosets_query, page, per_page)

  # Get photosets for current page
  photosets = photosets_query.paginate(page, per_page)

  # Add photo count and thumbnail for each photoset
  for photoset in photosets:
    photoset.photo_count = Photo.select().join(PhotoPhotoset).where(
      PhotoPhotoset.photoset == photoset
    ).count()

    # Get first photo as thumbnail
    first_photo = Photo.select().join(PhotoPhotoset).where(
      PhotoPhotoset.photoset == photoset
    ).order_by(Photo.datetaken.asc()).first()

    if first_photo:
      (sha1Path, filename) = getSha1Path(first_photo.sha1)
      photoset.thumb_uri = f'{sha1Path}/{filename}'
    else:
      photoset.thumb_uri = None

  return render_template('admin/photosets.html',
                        photosets=photosets,
                        pagination=pagination,
                        baseurl=get_base_url(),
                        search=search)


@app.route('/admin/photosets/create', methods=['GET', 'POST'])
@roles_required('admin')
def admin_create_photoset():
  """Create a new photoset"""
  if request.method == 'POST':
    title = request.form.get('title')
    description = request.form.get('description', '')

    if not title:
      flash('Title is required')
      return render_template('admin/create_photoset.html')

    try:
      photoset = Photoset.create(title=title, description=description)
      flash('Photoset created successfully')
      return redirect(url_for('admin_photosets'))
    except IntegrityError:
      flash('Photoset with that title already exists')

  return render_template('admin/create_photoset.html')


@app.route('/admin/photosets/<int:photoset_id>/edit', methods=['GET', 'POST'])
@roles_required('admin')
def admin_edit_photoset(photoset_id):
  """Edit photoset metadata"""
  photoset = Photoset.select().where(Photoset.id == photoset_id).get()

  if request.method == 'POST':
    photoset.title = request.form.get('title', photoset.title)
    photoset.description = request.form.get('description', '')
    photoset.save()

    flash('Photoset updated successfully')
    return redirect(url_for('admin_photosets'))

  return render_template('admin/edit_photoset.html', photoset=photoset)


@app.route('/admin/users')
@app.route('/admin/users/page/<int:page>')
@roles_required('admin')
def admin_users(page=1):
  """Admin user management interface"""
  per_page = app.config['PER_PAGE']

  # Optional search filter
  search = request.args.get('search', '')

  if search:
    # Search by email
    users_query = User.select().where(User.email.contains(search)).order_by(User.ts.desc())
  else:
    users_query = User.select().order_by(User.ts.desc())

  # Calculate pagination
  pagination = get_pagination_data(users_query, page, per_page)

  # Get paginated results
  users = users_query.paginate(page, per_page)

  # Add role information to each user
  for user in users:
    user.role_list = []
    for role in user.roles:
      user.role_list.append(role.name)

  return render_template('admin/users.html',
                        users=users,
                        pagination=pagination,
                        baseurl=get_base_url(),
                        search=search)


@app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@roles_required('admin')
def admin_edit_user(user_id):
  """Edit user roles and permissions"""
  user = User.select().where(User.id == user_id).get()

  if request.method == 'POST':
    # Update permission level
    permission_level = request.form.get('permission_level')
    if permission_level:
      user.permission_level = permission_level if permission_level != 'null' else None
      user.save()

    # Update roles
    roles = request.form.getlist('roles')

    # Remove existing roles
    UserRoles.delete().where(UserRoles.user == user).execute()

    # Add new roles
    for role_name in roles:
      role = Role.select().where(Role.name == role_name).first()
      if role:
        UserRoles.create(user=user, role=role)

    flash('User updated successfully')
    return redirect(url_for('admin_users'))

  # GET request - show edit form
  all_roles = Role.select()
  user_role_names = [role.name for role in user.roles]

  return render_template('admin/edit_user.html', user=user, all_roles=all_roles,
                        user_role_names=user_role_names)


# Share Link routes
@app.route('/photos/<int:photo_id>/share', methods=['POST'])
@login_required
def create_share_link(photo_id):
  """Create a shareable link for a photo"""
  photo = Photo.select().where(Photo.id == photo_id).get()

  # Check permission
  if not can_view_photo(current_user, photo):
    abort(403)

  # Get expiration days from form (default: 30 days)
  days = int(request.form.get('days', 30))
  expires_at = datetime.datetime.now() + datetime.timedelta(days=days) if days > 0 else None

  # Generate secure token
  token = secrets.token_urlsafe(32)

  # Create share token
  share_token = ShareToken.create(
    token=token,
    photo=photo,
    created_by_id=current_user.id,
    expires_at=expires_at
  )

  # Generate shareable URL
  share_url = f"{get_base_url()}/shared/{token}"

  # Store in session to display on next page load
  session['share_link'] = share_url
  session['share_expires'] = days

  flash(f'Share link created! Valid for {days} days.' if days > 0 else 'Share link created (no expiration).')
  return redirect(url_for('show_photo', photo_id=photo_id))


@app.route('/shared/<string:token>')
def view_shared_photo(token):
  """View a photo via share token"""
  try:
    share_token = ShareToken.select().where(ShareToken.token == token).get()
  except ShareToken.DoesNotExist:
    abort(404)

  # Check if token has expired
  if share_token.expires_at and share_token.expires_at < datetime.datetime.now():
    return render_template('shared/expired.html'), 410

  # Increment view count
  share_token.views += 1
  share_token.save()

  # Get photo
  photo = Photo.select().where(Photo.id == share_token.photo).get()
  (sha1Path, filename) = getSha1Path(photo.sha1)
  photo.uri = sha1Path + '/' + filename

  # Get tags
  tags = Tag.select().join(PhotoTag).where(PhotoTag.photo == photo.id)

  return render_template('shared/photo.html', photo=photo, tags=tags,
                        share_token=share_token)


@app.route('/admin/shares')
@app.route('/admin/shares/page/<int:page>')
@roles_required('admin')
def admin_shares(page=1):
  """Manage share links"""
  per_page = app.config['PER_PAGE']

  # Optional search filter
  search = request.args.get('search', '')

  if search:
    # Search by photo ID or token
    shares_query = (ShareToken
             .select(ShareToken, Photo)
             .join(Photo)
             .where((ShareToken.token.contains(search)) |
                   (Photo.id == search))
             .order_by(ShareToken.created_at.desc()))
  else:
    shares_query = (ShareToken
             .select(ShareToken, Photo)
             .join(Photo)
             .order_by(ShareToken.created_at.desc()))

  # Calculate pagination
  pagination = get_pagination_data(shares_query, page, per_page)

  # Get paginated results
  shares = shares_query.paginate(page, per_page)

  # Add photo URIs and check expiration
  for share in shares:
    (sha1Path, filename) = getSha1Path(share.photo.sha1)
    share.photo.uri = sha1Path + '/' + filename
    share.is_expired = share.expires_at and share.expires_at < datetime.datetime.now()

  return render_template('admin/shares.html',
                        shares=shares,
                        pagination=pagination,
                        baseurl=get_base_url(),
                        search=search)


@app.route('/admin/shares/<int:share_id>/revoke', methods=['POST'])
@roles_required('admin')
def admin_revoke_share(share_id):
  """Revoke a share link"""
  try:
    share_token = ShareToken.select().where(ShareToken.id == share_id).get()
    share_token.delete_instance()
    flash('Share link revoked')
  except ShareToken.DoesNotExist:
    flash('Share link not found')

  return redirect(url_for('admin_shares'))


if __name__ == '__main__':
  #init_db()
  app.run(port=app.config['PORT'])