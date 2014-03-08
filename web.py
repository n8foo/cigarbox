#! /usr/bin/env python

# -*- coding: utf-8 -*-
"""
    CigarBox
    ~~~~~~

    A smokin' fast personal photostream

    :copyright: (c) 2014 by Nathan Hubbard @n8foo.
    :license: Apache, see LICENSE for more details.
"""

import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash
import cigarbox.util

import argparse
parser = argparse.ArgumentParser(description='cigarbox webapp.')
args = parser.parse_args()

# create the app
app = Flask(__name__)

# Load default config and override config from config file
app.config.from_object('config')

remoteArchivePath=app.config['REMOTEARCHIVEPATH']

# Utility Functions

def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


def init_db():
    """Creates the database tables."""
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def get_db():
    """Opens DB connection if it none exists"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect_db()
    return db

def find(lst, key, value):
    for i, dic in enumerate(lst):
        if dic[key] == value:
            return i
    return -1

def paginate(page,perPage=app.config['PER_PAGE']):
    offset = (perPage * page) - perPage
    limit = (perPage * page)
    return(limit,offset)

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
    cur = query_db('SELECT id,sha1,fileType \
        FROM photos \
        ORDER BY id DESC \
        LIMIT ? OFFSET ?',paginate(page))
    photos = [dict(row) for row in cur]
    for photo in photos:
        (sha1Path,filename) = cigarbox.util.getSha1Path(photo['sha1'])
        photo['uri'] = sha1Path + '/' + filename
    return render_template('photostream.html', photos=photos, page=page, baseurl=baseurl)

@app.route('/photos/<int:photo_id>')
def show_photo(photo_id):
    """a single photo"""
    cur = query_db('SELECT id,sha1,fileType \
        FROM photos \
        WHERE id = ' + str(photo_id))
    # photos = cur.fetchall()
    photo = [dict(row) for row in cur][0]
    (sha1Path,filename) = cigarbox.util.getSha1Path(photo['sha1'])
    photo['uri'] = sha1Path + '/' + filename
    tags = query_db('SELECT tags.tag \
        FROM tags,tags_photos \
        WHERE tags.id=tag_id \
        AND photo_id = ?',[photo_id])
    return render_template('photos.html', photo=photo, tags=tags)

@app.route('/photos/<int:photo_id>/original')
def show_original_photo(photo_id):
    """a single authenticated original photo"""
    cur = query_db('SELECT id,sha1,fileType \
        FROM photos \
        WHERE id = ' + str(photo_id))
    photo = [dict(row) for row in cur][0]
    (sha1Path,filename) = cigarbox.util.getSha1Path(photo['sha1'])
    S3Key = '/'+sha1Path+'/'+filename+'.'+photo['fileType']
    if session:
        if session['logged_in'] == True:
            originalURL = cigarbox.aws.getPrivateURL(app.config,S3Key)
            return redirect(originalURL)
    else:
        return redirect('/login',code=302)


@app.route('/tags')
def show_tags():
    tags = query_db('SELECT tags.id,tags.tag,count(tags_photos.id) AS count \
        FROM tags,tags_photos \
        WHERE tags.id = tags_photos.tag_id \
        GROUP BY tag')
    return render_template('tag_cloud.html', tags=tags)

@app.route('/tags/<string:tag>', defaults={'page': 1})
@app.route('/tags/<string:tag>/page/<int:page>')
def show_taged_photos(tag,page):
    baseurl = '%s/tags/%s' % (app.config['SITEURL'],tag)
    (limit,offset) = paginate(page)
    cur = query_db('SELECT photos.id,photos.sha1,fileType \
        FROM photos,tags_photos,tags \
        WHERE photos.id = tags_photos.photo_id \
        AND tags_photos.tag_id = tags.id \
        AND tags.tag =  ? \
        ORDER BY photos.id DESC \
        LIMIT ? OFFSET ?',(tag,limit,offset))
    # photos = cur.fetchall()
    photos = [dict(row) for row in cur]
    for photo in photos:
        (sha1Path,filename) = cigarbox.util.getSha1Path(photo['sha1'])
        photo['uri'] = sha1Path + '/' + filename
    return render_template('photostream.html', photos=photos, page=page, baseurl=baseurl)

@app.route('/photosets', defaults={'page': 1})
@app.route('/photosets/page/<int:page>')
def show_photosets(page):
    thumbCount = 2
    baseurl = '%s/photosets' % (app.config['SITEURL'])
    (limit,offset) = paginate(page,perPage=52)
    cur = query_db('SELECT id,title \
        FROM photosets \
        ORDER BY ts DESC \
        LIMIT ? OFFSET ?',(limit,offset))
    photosets = [dict(row) for row in cur]
    for photoset in photosets:
        photoset_id = photoset['id']
        cur = query_db('SELECT photos.id,photos.sha1,fileType \
        FROM photos,photosets_photos \
        WHERE photos.id = photosets_photos.photo_id \
        AND photosets_photos.photoset_id = ? \
        ORDER BY photos.dateTaken DESC \
        LIMIT ?',(photoset_id,thumbCount,))
        photosetThumbs = [dict(row) for row in cur]
        for thumb in photosetThumbs:
            thumb['uri'] = '%s/%s_t.jpg' % (cigarbox.util.getSha1Path(thumb['sha1']))
        photoset['photosetThumbs'] = photosetThumbs
    return render_template('photosets.html', photosets=photosets, page=page, baseurl=baseurl)

@app.route('/photosets/<int:photoset_id>', defaults={'page': 1})
@app.route('/photosets/<int:photoset_id>/page/<int:page>')
def show_photoset(photoset_id,page):
    (limit,offset) = paginate(page)
    cur = query_db('SELECT photos.id,photos.sha1,fileType \
        FROM photos,photosets_photos \
        WHERE photos.id = photosets_photos.photo_id \
        AND photosets_photos.photoset_id = ? \
        ORDER BY photos.dateTaken DESC \
        LIMIT ? OFFSET ?',(photoset_id,limit,offset))
    photos = [dict(row) for row in cur]
    for photo in photos:
        (sha1Path,filename) = cigarbox.util.getSha1Path(photo['sha1'])
        photo['uri'] = sha1Path + '/' + filename
    photoset = query_db('SELECT id,title,description \
        FROM photosets \
        WHERE id = ?',[photoset_id],one=True)
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