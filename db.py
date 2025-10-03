#! /usr/bin/env python

import datetime
from peewee import *

from flask_security import Security, PeeweeUserDatastore, UserMixin, RoleMixin, login_required


from app import app

class UnknownField(object):
  pass

class BaseModel(Model):
  class Meta:
    database = SqliteDatabase(app.config['DATABASE']['name'])

class Photo(BaseModel):
  datetaken    = DateTimeField(null=True)
  filetype     = TextField(null=False)
  privacy      = IntegerField(null=True)
  sha1         = TextField(null=False,unique=True)
  ts           = DateTimeField(default=lambda: datetime.datetime.now())

class Comment(BaseModel):
  comment      = TextField(null=False)
  photo        = IntegerField(null=False)
  ts           = DateTimeField(default=lambda: datetime.datetime.now())

class Gallery(BaseModel):
  description  = TextField(null=True)
  title        = TextField(null=False,unique=True)
  ts           = DateTimeField(default=lambda: datetime.datetime.now())

class Photoset(BaseModel):
  description  = TextField(null=True)
  title        = TextField(null=False,unique=True)
  ts           = DateTimeField(default=lambda: datetime.datetime.now())

class Tag(BaseModel):
  name         = TextField(null=False,unique=True)
  ts           = DateTimeField(default=lambda: datetime.datetime.now())

class PhotoPhotoset(BaseModel):
  photo        = ForeignKeyField(Photo,null=False)
  photoset     = ForeignKeyField(Photoset,null=False)
  ts           = DateTimeField(default=lambda: datetime.datetime.now())

class PhotosetGallery(BaseModel):
  gallery      = ForeignKeyField(Gallery,null=False)
  photoset     = ForeignKeyField(Photoset,null=False)
  ts           = DateTimeField(default=lambda: datetime.datetime.now())

class PhotoTag(BaseModel):
  photo        = ForeignKeyField(Photo,null=False)
  tag          = ForeignKeyField(Tag,null=False)
  ts           = DateTimeField(default=lambda: datetime.datetime.now())

class ImportMeta(BaseModel):
  sha1         = TextField(null=False,unique=True)
  photo        = IntegerField(null=False)
  importpath   = TextField(null=True)
  importsource = TextField(null=True)
  filedate     = DateTimeField(null=True)
  s3           = IntegerField(null=True)
  ts           = DateTimeField(default=lambda: datetime.datetime.now())

class Role(BaseModel, RoleMixin):
  name         = CharField(unique=True)
  description  = TextField(null=True)


class User(BaseModel, UserMixin):
  email        = TextField(unique=True)
  password     = TextField(null=False)
  active       = BooleanField(default=True)
  confirmed_at = DateTimeField(null=True)
  ts           = DateTimeField(default=lambda: datetime.datetime.now())

class UserRoles(BaseModel):
  user         = ForeignKeyField(User, related_name='role')
  role         = ForeignKeyField(Role, related_name='user')
  name         = property(lambda self: self.role.name)
  description  = property(lambda self: self.role.description)

