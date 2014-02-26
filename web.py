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

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def photostream():
    """the list of the most recently added pictures"""
    cur = query_db('SELECT id,sha1,fileType \
        FROM photos \
        ORDER BY id DESC \
        LIMIT 200')
    photos = [dict(row) for row in cur]
    for photo in photos:
        (sha1Path,filename) = cigarbox.util.getSha1Path(photo['sha1'])
        photo['uri'] = sha1Path + '/' + filename
    return render_template('photostream.html', photos=photos)

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

@app.route('/tags')
def show_tags():
    tags = query_db('SELECT tags.id,tags.tag,count(tags_photos.id) AS count \
        FROM tags,tags_photos \
        WHERE tags.id = tags_photos.tag_id \
        GROUP BY tag')
    return render_template('tag_cloud.html', tags=tags)

@app.route('/tags/<string:tag>')
def show_taged_photos(tag):
    cur = query_db('SELECT photos.id,photos.sha1,fileType \
        FROM photos,tags_photos,tags \
        WHERE photos.id = tags_photos.photo_id \
        AND tags_photos.tag_id = tags.id \
        AND tags.tag =  ? \
        ORDER BY photos.id DESC \
        LIMIT 500',[tag])
    # photos = cur.fetchall()
    photos = [dict(row) for row in cur]
    for photo in photos:
        (sha1Path,filename) = cigarbox.util.getSha1Path(photo['sha1'])
        photo['uri'] = sha1Path + '/' + filename
    return render_template('photostream.html', photos=photos)

@app.route('/photosets')
def show_photosets():
    photosets = query_db('SELECT id,title \
        FROM photosets \
        ORDER BY ts DESC \
        LIMIT 50')
    return render_template('photosets.html', photosets=photosets)

@app.route('/photosets/<int:photoset_id>')
def show_photoset(photoset_id):
    cur = query_db('SELECT photos.id,photos.sha1,fileType \
        FROM photos,photosets_photos \
        WHERE photos.id = photosets_photos.photo_id \
        AND photosets_photos.photoset_id = ? \
        ORDER BY photos.dateTaken DESC \
        LIMIT 500',[photoset_id])
    photos = [dict(row) for row in cur]
    for photo in photos:
        (sha1Path,filename) = cigarbox.util.getSha1Path(photo['sha1'])
        photo['uri'] = sha1Path + '/' + filename
    photoset = query_db('SELECT id,title,description \
        FROM photosets \
        WHERE id = ?',[photoset_id],one=True)
    return render_template('photoset.html', photos=photos, photoset=photoset)

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
            return redirect(url_for('show_photos'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_photos'))


if __name__ == '__main__':
    #init_db()
    app.run()