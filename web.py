#! /usr/bin/env python

# -*- coding: utf-8 -*-
"""
  CigarBox
  ~~~~~~

  A smokin' fast personal photostream

  :copyright: (c) 2015 by Nathan Hubbard @n8foo.
  :license: Apache, see LICENSE for more details.
"""

from flask import Flask, request, session, g, redirect, url_for, abort, \
  render_template, flash, send_from_directory

from flask.ext.security import Security, PeeweeUserDatastore, UserMixin, RoleMixin, login_required

from werkzeug import secure_filename

from app import app
from util import *
from db import *


# Utility Functions

def find(lst, key, value):
  for i, dic in enumerate(lst):
    if dic[key] == value:
      return i
  return -1

# URL Routing

@app.errorhandler(404)
def page_not_found(error):
  return render_template('404.html'), 404

@app.errorhandler(500)
def page_not_found(error):
  return render_template('404.html'), 404

@app.teardown_appcontext
def close_db(error):
  """Closes the database again at the end of the request."""
  db = getattr(g, '_database', None)
  if db is not None:
    db.close()

@app.route('/', defaults={'page': 1})
@app.route('/photostream', defaults={'page': 1})
@app.route('/photostream/page/<int:page>')
def photostream(page):
  """the list of the most recently added pictures"""
  baseurl = '%s/photostream' % (app.config['SITEURL'])
  photos = Photo.select()
  photos = photos.order_by(Photo.id.desc())
  photos = photos.paginate(page,app.config['PER_PAGE'])
  for photo in photos:
    (sha1Path,filename) = getSha1Path(photo.sha1)
    photo.uri = sha1Path + '/' + filename
  return render_template('photostream.html', photos=photos, page=page, baseurl=baseurl)

@app.route('/photos/<int:photo_id>')
def show_photo(photo_id):
  """a single photo"""
  photo = Photo.select().where(Photo.id == photo_id).get()
  (sha1Path,filename) = getSha1Path(photo.sha1)
  photo.uri = sha1Path + '/' + filename
  tags = Tag.select().join(PhotoTag).where(PhotoTag.photo == photo_id)
  return render_template('photos.html', photo=photo, tags=tags)

@app.route('/photos/<int:photo_id>/original')
def show_original_photo(photo_id):
  """a single authenticated original photo"""
  photo = Photo.select().where(Photo.id == photo_id).get()
  (sha1Path,filename) = getSha1Path(photo.sha1)
  S3Key = '/'+sha1Path+'/'+filename+'.'+photo.filetype
  originalURL = aws.getPrivateURL(app.config,S3Key)
  return redirect(originalURL)

@app.route('/tags')
def show_tags():
  tags = Tag.select().annotate(PhotoTag)
  return render_template('tag_cloud.html', tags=tags)

@app.route('/tags/<string:tag>', defaults={'page': 1})
@app.route('/tags/<string:tag>/page/<int:page>')
def show_taged_photos(tag,page):
  baseurl = '%s/tags/%s' % (app.config['SITEURL'],tag)
  photos = Photo.select().join(PhotoTag).join(Tag)
  photos = photos.where(Tag.name == tag)
  photos = photos.order_by(Photo.id.desc())
  photos = photos.paginate(page,app.config['PER_PAGE'])
  for photo in photos:
    (sha1Path,filename) = getSha1Path(photo.sha1)
    photo.uri = sha1Path + '/' + filename
  return render_template('photostream.html', photos=photos, page=page, baseurl=baseurl)

@app.route('/date/<string:date>', defaults={'page': 1})
@app.route('/date/<string:date>/page/<int:page>')
def show_date_photos(date,page):
  baseurl = '%s/date/%s' % (app.config['SITEURL'],date)

  photos = Photo.select()
  photos = photos.where(Photo.datetaken.startswith(date))
  photos = photos.order_by(Photo.datetaken.desc())
  photos = photos.paginate(page,app.config['PER_PAGE'])
  for photo in photos:
    (sha1Path,filename) = getSha1Path(photo.sha1)
    photo.uri = sha1Path + '/' + filename
  return render_template('photostream.html', photos=photos, page=page, baseurl=baseurl)

@app.route('/tags/<string:tag>/delete')
@login_required
def delete_tag(tag):
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
def delete_photo(photo_id):
  # delete from any photoset
  #deletePhotoPhotoset = PhotoPhotoset.delete().where(PhotoPhotoset.photo == Photo.id)
  #deletePhotoPhotoset.execute()
  # remove associated tags
  #deletePhotoPhotoset = PhotoPhotoset.delete().where(PhotoPhotoset.photo == Photo.id)
  #deletePhotoPhotoset.execute()
  # delete photo from S3 (not working)
  #photo = Photo.select().where(Photo.id == photo_id).get()
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
  baseurl = '%s/photosets' % (app.config['SITEURL'])
  photosets = Photoset.select()
  photosets = photosets.order_by(Photoset.ts.desc())
  photosets = photosets.paginate(page,app.config['PER_PAGE'])
  for photoset in photosets:
    thumbs = Photo.select().join(PhotoPhotoset).join(Photoset)
    thumbs = thumbs.where(Photoset.id == photoset.id)
    thumbs = thumbs.limit(thumbCount)
    thumbs = thumbs.order_by(Photo.datetaken.asc())
    for thumb in thumbs:
      thumb.uri = '%s/%s_t.jpg' % (getSha1Path(thumb.sha1))
    photoset.thumbs = thumbs
  return render_template('photosets.html', photosets=photosets, page=page, baseurl=baseurl)

@app.route('/photosets/<int:photoset_id>', defaults={'page': 1})
@app.route('/photosets/<int:photoset_id>/page/<int:page>')
def show_photoset(photoset_id,page):
  photos = Photo.select().join(PhotoPhotoset).join(Photoset)
  photos = photos.where(Photoset.id == photoset_id)
  photos = photos.order_by(Photo.datetaken.asc())
  photos = photos.paginate(page,100)
  for photo in photos:
    (sha1Path,filename) = getSha1Path(photo.sha1)
    photo.uri = sha1Path + '/' + filename
  photoset = Photoset.select().where(Photoset.id == photoset_id)
  photoset = photoset.get()
  return render_template('photoset.html', photos=photos, photoset=photoset, page=page)

@app.route('/photosets/<int:photoset_id>/delete')
#@login_required
def delete_photoset(photoset_id):
  # clean up relationships to soon-to-be deleted photoset
  #PhotoPhotoset.delete().where(PhotoPhotoset.photoset == photoset_id).execute
  # delete photoset
  photoset = Photoset.get(Photoset.id == photoset_id)
  photoset.delete_instance(recursive=True)
  flash('Photoset deleted')
  return redirect(url_for('photostream'))

@app.route('/photosets/<int:photoset_id>/deletephotos')
#@login_required
def delete_photoset_photos(photoset_id):
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
def show_photo_from_md5(sha1):
  """a single photo"""
  try:
    photo = Photo.select().where(Photo.sha1 == sha1).get()
  except Exception, e:
    page_not_found('no sha1 found')
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

# upload

# For a given file, return whether it's an allowed type or not
def allowed_file(filename):
  return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/upload', methods=['POST'])
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


if __name__ == '__main__':
  #init_db()
  app.run(port=app.config['PORT'])