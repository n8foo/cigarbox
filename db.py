#! /usr/bin/env python

import datetime
from peewee import *

from flask_peewee.db import Database
from flask.ext.security import Security, PeeweeUserDatastore, UserMixin, RoleMixin, login_required


from app import app

db = Database(app)

class UnknownField(object):
    pass

class Photo(db.Model):
    datetaken    = DateTimeField(db_column='dateTaken', null=True)
    filetype     = TextField(db_column='fileType')
    privacy      = IntegerField(null=True)
    sha1         = TextField(null=False)
    ts           = DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = 'photos'

class Comment(db.Model):
    comment      = TextField(null=False)
    photo        = IntegerField(db_column='photo_id', null=False)
    ts           = DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = 'comments'

class Gallery(db.Model):
    description  = TextField(null=True)
    title        = TextField(null=False)
    ts           = DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = 'galleries'

class Photoset(db.Model):
    description  = TextField(null=True)
    title        = TextField(null=False)
    ts           = DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = 'photosets'

class Tag(db.Model):
    name         = TextField(null=False,db_column='tag')
    ts           = DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = 'tags'

class PhotoPhotoset(db.Model):
    photo        = ForeignKeyField(Photo,db_column='photo_id', null=False)
    photoset     = ForeignKeyField(Photoset,db_column='photoset_id', null=False)
    ts           = DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = 'photosets_photos'

class PhotosetGallery(db.Model):
    gallery      = ForeignKeyField(Gallery,db_column='galleries_id', null=False)
    photoset     = ForeignKeyField(Photoset,db_column='photoset_id', null=False)
    ts           = DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = 'galleries_photosets'

class PhotoTag(db.Model):
    photo        = ForeignKeyField(Photo,db_column='photo_id', null=False)
    tag          = ForeignKeyField(Tag,db_column='tag_id', null=False)
    ts           = DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = 'tags_photos'

class ImportMeta(db.Model):
    s3           = IntegerField(db_column='S3', null=True)
    filedate     = DateTimeField(db_column='fileDate', null=True)
    importpath   = TextField(db_column='importPath', null=True)
    importsource = TextField(db_column='importSource', null=True)
    photo        = ForeignKeyField(Photo,db_column='photo_id', null=False)
    ts           = DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = 'import_meta'

class Role(db.Model, RoleMixin):
    name         = CharField(unique=True)
    description  = TextField(null=True)

class User(db.Model, UserMixin):
    email        = TextField(unique=True)
    password     = TextField(null=False)
    active       = BooleanField(default=True)
    confirmed_at = DateTimeField(null=True)
    ts           = DateTimeField(default=datetime.datetime.now)


class UserRoles(db.Model):
    user         = ForeignKeyField(User, related_name='roles')
    role         = ForeignKeyField(Role, related_name='users')
    name         = property(lambda self: self.role.name)
    description  = property(lambda self: self.role.description)



