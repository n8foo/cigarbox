#! /usr/bin/env python

import datetime
from peewee import *

from flask.ext.security import Security, PeeweeUserDatastore, UserMixin, RoleMixin, login_required


from app import app

db = SqliteDatabase(app.config['DATABASE']['name'])

class UnknownField(object):
  pass

class Photo(Model):
  datetaken    = DateTimeField(null=True)
  filetype     = TextField(null=False)
  privacy      = IntegerField(null=True)
  sha1         = TextField(null=False,unique=True)
  ts           = DateTimeField(default=datetime.datetime.now)
  class Meta:
    database = db

class Comment(Model):
  comment      = TextField(null=False)
  photo        = IntegerField(null=False)
  ts           = DateTimeField(default=datetime.datetime.now)
  class Meta:
    database = db

class Gallery(Model):
  description  = TextField(null=True)
  title        = TextField(null=False,unique=True)
  ts           = DateTimeField(default=datetime.datetime.now)
  class Meta:
    database = db

class Photoset(Model):
  description  = TextField(null=True)
  title        = TextField(null=False,unique=True)
  ts           = DateTimeField(default=datetime.datetime.now)
  class Meta:
    database = db

class Tag(Model):
  name         = TextField(null=False,unique=True)
  ts           = DateTimeField(default=datetime.datetime.now)
  class Meta:
    database = db

class PhotoPhotoset(Model):
  photo        = ForeignKeyField(Photo,null=False)
  photoset     = ForeignKeyField(Photoset,null=False)
  ts           = DateTimeField(default=datetime.datetime.now)
  class Meta:
    database = db

class PhotosetGallery(Model):
  gallery      = ForeignKeyField(Gallery,null=False)
  photoset     = ForeignKeyField(Photoset,null=False)
  ts           = DateTimeField(default=datetime.datetime.now)
  class Meta:
    database = db

class PhotoTag(Model):
  photo        = ForeignKeyField(Photo,null=False)
  tag          = ForeignKeyField(Tag,null=False)
  ts           = DateTimeField(default=datetime.datetime.now)
  class Meta:
    database = db

class ImportMeta(Model):
  sha1         = TextField(null=False,unique=True)
  photo        = IntegerField(null=False)
  importpath   = TextField(null=True)
  importsource = TextField(null=True)
  filedate     = DateTimeField(null=True)
  s3           = IntegerField(null=True)
  ts           = DateTimeField(default=datetime.datetime.now)
  class Meta:
    database = db

class Role(Model, RoleMixin):
  name         = CharField(unique=True)
  description  = TextField(null=True)

class User(Model, UserMixin):
  email        = TextField(unique=True)
  password     = TextField(null=False)
  active       = BooleanField(default=True)
  confirmed_at = DateTimeField(null=True)
  ts           = DateTimeField(default=datetime.datetime.now)
  class Meta:
    database = db


class UserRoles(Model):
  user         = ForeignKeyField(User, related_name='role')
  role         = ForeignKeyField(Role, related_name='user')
  name         = property(lambda self: self.role.name)
  description  = property(lambda self: self.role.description)
  class Meta:
    database = db



