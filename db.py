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
  datetaken    = DateTimeField(null=True)
  filetype     = TextField(null=False)
  privacy      = IntegerField(null=True)
  sha1         = TextField(null=False,unique=True)
  ts           = DateTimeField(default=datetime.datetime.now)

class Comment(db.Model):
  comment      = TextField(null=False)
  photo        = IntegerField(null=False)
  ts           = DateTimeField(default=datetime.datetime.now)

class Gallery(db.Model):
  description  = TextField(null=True)
  title        = TextField(null=False,unique=True)
  ts           = DateTimeField(default=datetime.datetime.now)

class Photoset(db.Model):
  description  = TextField(null=True)
  title        = TextField(null=False,unique=True)
  ts           = DateTimeField(default=datetime.datetime.now)

class Tag(db.Model):
  name         = TextField(null=False,unique=True)
  ts           = DateTimeField(default=datetime.datetime.now)

class PhotoPhotoset(db.Model):
  photo        = ForeignKeyField(Photo,null=False)
  photoset     = ForeignKeyField(Photoset,null=False)
  ts           = DateTimeField(default=datetime.datetime.now)

class PhotosetGallery(db.Model):
  gallery      = ForeignKeyField(Gallery,null=False)
  photoset     = ForeignKeyField(Photoset,null=False)
  ts           = DateTimeField(default=datetime.datetime.now)

class PhotoTag(db.Model):
  photo        = ForeignKeyField(Photo,null=False)
  tag          = ForeignKeyField(Tag,null=False)
  ts           = DateTimeField(default=datetime.datetime.now)

class ImportMeta(db.Model):
  sha1         = TextField(null=False,unique=True)
  photo        = IntegerField(null=False)
  importpath   = TextField(null=True)
  importsource = TextField(null=True)
  filedate     = DateTimeField(null=True)
  s3           = IntegerField(null=True)
  ts           = DateTimeField(default=datetime.datetime.now)

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
  user         = ForeignKeyField(User, related_name='role')
  role         = ForeignKeyField(Role, related_name='user')
  name         = property(lambda self: self.role.name)
  description  = property(lambda self: self.role.description)



