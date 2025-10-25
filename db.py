#! /usr/bin/env python

import datetime
from peewee import *

from flask_security import Security, PeeweeUserDatastore, UserMixin, RoleMixin, login_required


from app import app

class UnknownField(object):
  pass

# Create database instance with foreign key constraints enabled
db = SqliteDatabase(app.config['DATABASE']['name'], pragmas={'foreign_keys': 1})

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
  photo        = ForeignKeyField(Photo, backref='import_meta', on_delete='CASCADE')
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

  def get_permissions(self):
    """Stub for Flask-Principal compatibility (we don't use permissions)"""
    return []


class User(BaseModel, UserMixin):
  email        = TextField(unique=True)
  password     = TextField(null=False)
  active       = BooleanField(default=True)
  confirmed_at = DateTimeField(null=True)
  fs_uniquifier = TextField(unique=True, null=True)  # Required by Flask-Security-Too 5.x
  permission_level = CharField(null=True)  # 'private', 'family', 'friends', 'public'
  ts           = DateTimeField(default=lambda: datetime.datetime.now())

  @property
  def roles(self):
    """Return actual Role objects (Flask-Security compatibility)
    Override the Peewee backref to return Role objects instead of UserRoles objects"""
    return [ur.role for ur in UserRoles.select().where(UserRoles.user == self)]

  def has_role(self, role_name):
    """Override to check role by name (Flask-Security compatibility)"""
    for role in self.roles:
      if role.name == role_name:
        return True
    return False

class UserRoles(BaseModel):
  user         = ForeignKeyField(User, related_name='user_roles_set')
  role         = ForeignKeyField(Role, related_name='role_users_set')
  name         = property(lambda self: self.role.name)
  description  = property(lambda self: self.role.description)

