#! /usr/bin/env python

# -*- coding: utf-8 -*-
"""
    CigarBox
    ~~~~~~

    A smokin' fast personal photostream

    :copyright: (c) 2014 by Nathan Hubbard @n8foo.
    :license: Apache, see LICENSE for more details.
"""

from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash
from cigarbox.util import *
from cigarbox.orm import *


# create the app
app = Flask(__name__)

# Load default config and override config from config file
app.config.from_object('config')

remoteArchivePath=app.config['REMOTEARCHIVEPATH']

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
    if session:
        if session['logged_in'] == True:
            originalURL = aws.getPrivateURL(app.config,S3Key)
            return redirect(originalURL)
    else:
        return redirect('/login',code=302)


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

@app.route('/add', methods=['POST'])
def add_photo():
    if not session.get('logged_in'):
        abort(401)
    #db = get_db()
    #db.execute('insert into photos (title, text) values (?, ?)',
    #             [request.form['title'], request.form['text']])
    #db.commit()
    flash('New photo was successfully posted')
    return redirect(url_for('show_photos'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('photostream'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('photostream'))


if __name__ == '__main__':
    #init_db()
    app.run()