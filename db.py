#! /usr/bin/env python

import datetime
from peewee import *

from flask_security import Security, PeeweeUserDatastore, UserMixin, RoleMixin, login_required


from app import app

class UnknownField(object):
  pass

# Create database instance
db = SqliteDatabase(app.config['DATABASE']['name'])

class BaseModel(Model):
  class Meta:
    database = db

class Photo(BaseModel):
  datetaken    = DateTimeField(null=True)
  filetype     = TextField(null=False)
  privacy      = IntegerField(null=True)
  sha1         = TextField(null=False,unique=True)
  uploaded_by_id = IntegerField(null=True)  # Foreign key to User.id (set by migration)
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

class ShareToken(BaseModel):
  token        = CharField(unique=True, null=False)
  photo        = ForeignKeyField(Photo, backref='share_tokens')
  created_by_id = IntegerField(null=True)  # Foreign key to User.id
  created_at   = DateTimeField(default=lambda: datetime.datetime.now())
  expires_at   = DateTimeField(null=True)
  views        = IntegerField(default=0)

class Role(BaseModel, RoleMixin):
  name         = CharField(unique=True)
  description  = TextField(null=True)


class User(BaseModel, UserMixin):
  email        = TextField(unique=True)
  password     = TextField(null=False)
  active       = BooleanField(default=True)
  confirmed_at = DateTimeField(null=True)
  fs_uniquifier = TextField(unique=True, null=True)  # Required by Flask-Security-Too 5.x
  permission_level = CharField(null=True)  # 'private', 'family', 'friends', 'public'
  ts           = DateTimeField(default=lambda: datetime.datetime.now())

  def has_role(self, role_name):
    """Override to check role by name (Flask-Security compatibility)"""
    user_roles = UserRoles.select().where(UserRoles.user == self)
    for ur in user_roles:
      if ur.role.name == role_name:
        return True
    return False

class UserRoles(BaseModel):
  user         = ForeignKeyField(User, related_name='user_roles')
  role         = ForeignKeyField(Role, related_name='role_users')
  name         = property(lambda self: self.role.name)
  description  = property(lambda self: self.role.description)

