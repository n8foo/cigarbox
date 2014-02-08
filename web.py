#! /usr/bin/env python

# -*- coding: utf-8 -*-
"""
    CigarBox
    ~~~~~~

    A smokin' fast personal photostream

    :copyright: (c) 2014 by Nathan Hubbard @n8foo.
    :license: Apache, see LICENSE for more details.
"""

from sqlite3 import dbapi2 as sqlite3
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


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


@app.route('/')
def show_photos():
    db = get_db()
    cur = db.execute('select id,sha1,fileType from photos order by id desc limit 10')
    # photos = cur.fetchall()
    photos = [dict(row) for row in cur]
    for photo in photos:
        photo['uri'] = cigarbox.util.getArchiveURI(photo['sha1'],remoteArchivePath,photo['fileType'])
    return render_template('show_photos.html', photos=photos)

@app.route('/tags')
def show_tags():
    db = get_db()
    cur = db.execute('select tags.id,tags.tag,count(tags_photos.id) as count from tags,tags_photos where tags.id = tags_photos.tag_id group by tag')
    tags = cur.fetchall()
    return render_template('tag_cloud.html', tags=tags)


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