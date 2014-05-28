#! /usr/bin/env python

import datetime
from peewee import *


database = SqliteDatabase('photos.db', **{})

class UnknownField(object):
    pass

class BaseModel(Model):
    class Meta:
        database = database

class Photo(BaseModel):
    datetaken    = DateTimeField(db_column='dateTaken', null=True)
    filetype     = TextField(db_column='fileType')
    privacy      = IntegerField(null=True)
    sha1         = TextField(null=False)
    ts           = DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = 'photos'

class Comment(BaseModel):
    comment      = TextField(null=True)
    photo        = IntegerField(db_column='photo_id', null=True)
    ts           = DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = 'comments'

class Gallery(BaseModel):
    description  = TextField(null=True)
    title        = TextField(null=False)
    ts           = DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = 'galleries'

class Photoset(BaseModel):
    description  = TextField(null=True)
    title        = TextField(null=False)
    ts           = DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = 'photosets'

class Tag(BaseModel):
    name         = TextField(null=False,db_column='tag')
    ts           = DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = 'tags'

class PhotoPhotoset(BaseModel):
    photo        = ForeignKeyField(Photo,db_column='photo_id')
    photoset     = ForeignKeyField(Photoset,db_column='photoset_id')
    ts           = DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = 'photosets_photos'

class PhotosetGallery(BaseModel):
    gallery      = ForeignKeyField(Gallery,db_column='galleries_id', null=True)
    photoset     = ForeignKeyField(Photoset,db_column='photoset_id', null=True)
    ts           = DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = 'galleries_photosets'

class PhotoTag(BaseModel):
    photo        = ForeignKeyField(Photo,db_column='photo_id', null=True)
    tag          = ForeignKeyField(Tag,db_column='tag_id', null=True)
    ts           = DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = 'tags_photos'

class ImportMeta(BaseModel):
    s3           = IntegerField(db_column='S3', null=True)
    filedate     = DateTimeField(db_column='fileDate', null=True)
    importpath   = TextField(db_column='importPath', null=True)
    importsource = TextField(db_column='importSource', null=True)
    photo        = ForeignKeyField(Photo,db_column='photo_id', null=False)
    ts           = DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = 'import_meta'
