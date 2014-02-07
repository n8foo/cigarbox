#!/usr/bin/env python

# -*- coding: utf-8 -*-
"""
    CigarBox
    ~~~~~~

    A smokin' fast personal photo archive, written in
    Flask and sqlite3.

    :copyright: (c) 2014 by Nathan Hubbard @n8foo.
    :license: Apache, see LICENSE for more details.
"""

from sqlite3 import dbapi2 as sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash


# create the app
app = Flask(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE='photos.db',
    DEBUG=True,
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='changeme2014'
))
app.config.from_envvar('CIGARBOX_SETTINGS', silent=True)


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

def getArchivePath(sha1):
    """Returns archive directory"""
    dir1=sha1[:2]
    dir2=sha1[2:4]
    dir3=sha1[4:6]
    return(dir1+'/'+dir2+'/'+dir3)

def getArchiveURI(sha1):
    """Returns the full path to archive image"""
    archivePath=getArchivePath(sha1)
    return(basedir+'/'+archivePath+'/'+sha1+'.'+fileType)


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


@app.route('/')
def show_photos():
    db = get_db()
    cur = db.execute('select id,sha1 from photos order by id desc limit 10')
    photos = cur.fetchall()
    return render_template('show_photos.html', photos=photos)


@app.route('/add', methods=['POST'])
def add_entry():
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    db.execute('insert into photos (title, text) values (?, ?)',
                 [request.form['title'], request.form['text']])
    db.commit()
    flash('New entry was successfully posted')
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