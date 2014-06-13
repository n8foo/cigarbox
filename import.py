#! /usr/bin/env python

# -*- coding: utf-8 -*-
"""
    CigarBox
    ~~~~~~

    A smokin' fast personal photostream

    :copyright: (c) 2014 by Nathan Hubbard @n8foo.
    :license: Apache, see LICENSE for more details.
"""

import argparse

parser = argparse.ArgumentParser(description='import photos into photos system.')
parser.add_argument('--files', metavar='N', type=str, nargs='+',
                   help='files to import', required=True)
#parser.add_argument('--gallery', help='assign a gallery to an import')
parser.add_argument('--tags', help='assign comma separated tag(s) to an import')
parser.add_argument('--dirtags', help='tag photos based on directory structure', action='store_true')
parser.add_argument('--photoset', help='add this import to a photoset')
parser.add_argument('--parentdirphotoset', help='assign a photoset name based on parent directory', action='store_true', default=False)
parser.add_argument('--regen', help='regenerate thumbnails', action='store_true', default=False)
parser.add_argument('--S3', help='upload to S3', action='store_true')
parser.add_argument('--privacy', help='set privacy on a photo, default is public', choices=['public','family','friends','private','disabled'], default='public')
parser.add_argument('--importsource', help='override import source')
args = parser.parse_args()

import os, sqlite3, shutil, time, datetime
import util, aws
from db import *

logger = util.setup_custom_logger('cigarbox')
logger.info('starting import....')

from flask import Flask, g
app = Flask(__name__)

# Load default config and override config from config file
app.config.from_object('config')

localArchivePath=app.config['LOCALARCHIVEPATH']

@app.teardown_appcontext
def teardown_db(exception):
  """Closes the database again at the end of the request."""
  db = getattr(g, '_database', None)
  if db is not None:
      db.close()

def photosetsCreate(title,description=None):
  """create a photoset - takes title and optional description. returns id"""
  try:
    photoset = Photoset.get(Photoset.title == title)
  except Photoset.DoesNotExist:
    logger.info('creating photoset: %s',title)
    photoset = Photoset.create(title=title,description=description)
  return photoset.id

def saveImportMeta(photo_id,filename,importSource=args.importsource,S3=False):
  importPath = os.path.abspath(filename)
  fileDate = time.ctime(os.path.getmtime(filename))
  try:
    meta = ImportMeta.get(ImportMeta.photo == photo_id)
  except ImportMeta.DoesNotExist:
    meta = ImportMeta.create(photo=photo_id,filedate=fileDate,importpath=importPath,importsource=importSource,s3=S3)
    logger.info('recording import meta for photo id: %s',photo_id)
  return meta.id

def checkImportStatusS3(photo_id):
  try:
    importStatusS3 = ImportMeta.get(ImportMeta.photo == photo_id,ImportMeta.s3 == True)
    return True
  except ImportMeta.DoesNotExist:
    return False

def photosetsAddPhoto(photoset_id,photo_id):
  try:
    PhotoPhotoset.get(PhotoPhotoset.photoset == photoset_id,PhotoPhotoset.photo == photo_id)
    return True
  except PhotoPhotoset.DoesNotExist:
    PhotoPhotoset.create(photoset=photoset_id,photo=photo_id)
    logger.info('adding photo id: %s to photoset id: %s',photo_id,photoset_id,)
  except Exception, e:
    return e

def getSha1FromPhotoID (photo_id):
  photo = Photo.get(Photo.id == photo_id)
  return(photo.sha1)

def getOriginalPhotoName (photo_id):
  sha1 = getSha1FromPhotoID(photo_id)
  secret_key = app.config['SECRET_KEY']
  # some as yet undefined sorcery
  return(originalPhotoName)


def addPhotoToDB(sha1,fileType,dateTaken,privacy):
  """adds photo to photos table, returns photo_id"""
  # set privacy
  privacyNum = app.config['PRIVACYFLAGS'][privacy]
  try:
    photo = Photo.get(Photo.sha1 == sha1)
    return photo.id
  except Photo.DoesNotExist:
    logger.info('Adding to DB: %s %s %s %s', sha1,fileType,dateTaken,privacy)
    photo = Photo.create(sha1=sha1,filetype=fileType,datetaken=dateTaken,privacy=privacyNum)
    return photo.id
  except Exception, e:
    return e

def photosAddTag(photo_id,tag):
  """add tags to a photo: takes photo id and tag. normalizes tag. returns tag id"""
  normalizedtag = util.normalizeString(tag)
  # create the tag first
  try:
    tagobject = Tag.get(Tag.name == normalizedtag)
  except Tag.DoesNotExist:
    tagobject = Tag.create(name = normalizedtag)
  except Exception as e:
    raise e
  # ok now we have the tag_id and photo_id, let's do this
  try:
    phototag = PhotoTag.get(PhotoTag.photo == photo_id,PhotoTag.tag == tagobject.id)
    return id
  except PhotoTag.DoesNotExist:
    logger.info('tagging photo id %s tag: %s', photo_id, tag)
    phototag = PhotoTag.create(photo=photo_id,tag=tagobject.id)
  except Exception, e:
    return e

def getfileType(filename):
  fileType = filename.split('.')[-1].lower()
  return fileType

def archivePhoto(file,sha1,fileType,localArchivePath,args,photo_id):
  (sha1Path,sha1Filename)=util.getSha1Path(sha1)
  archivedPhoto='%s/%s/%s.%s' % (localArchivePath,sha1Path,sha1Filename,fileType)
  if not os.path.isdir(localArchivePath+'/'+sha1Path):
    os.makedirs(localArchivePath+'/'+sha1Path)
  if not os.path.isfile(archivedPhoto):
    try:
      logger.info('Copying %s -> %s',file,archivedPhoto)
      shutil.copy2(file,archivedPhoto)
    except Exception, e:
      raise e
  if args.S3 == True:
    if checkImportStatusS3(photo_id) == False:
      S3Key='%s/%s.%s' % (sha1Path,sha1Filename,fileType)
      aws.uploadToS3(file,S3Key,app.config,policy=app.config['AWSPOLICY'])
  return(archivedPhoto)

def dirTags(photo_id,file,ignoreTags):
  # add tags based on directory structure
  osPathDirnames = os.path.dirname(file).split('/')
  dirTags = []
  for osPathDirname in osPathDirnames:
    tag = str(osPathDirname)
    if tag != '':
      if tag not in ignoreTags:
        dirTags.append(tag)
        photosAddTag(photo_id,tag)
  return dirTags

def parentDirPhotoSet(photo_id,file):
  # add tags based on parent directory
  parentDir = osPathDirnames = os.path.dirname(file).split('/')[-1]
  photoset_id = photosetsCreate(parentDir)
  photosetsAddPhoto(photoset_id,photo_id)
  return True



def main():
  """Main program"""
  logger.info('Starting Import')
  if args.photoset:
    photoset_id = photosetsCreate(args.photoset)

  for filename in args.files:
    # log what we're doing
    logger.info('Scanning file %s', filename)
    # get a date, from exif or file
    try:
      exifDateTaken = util.getExifTags(filename)['DateTimeOriginal']
      dateTaken = datetime.datetime.strptime(exifDateTaken, "%Y:%m:%d %H:%M:%S" )
    except Exception, e:
      dateTaken = None

    # set some variables
    fileType = getfileType(os.path.basename(filename))
    sha1=util.hashfile(filename)

    # insert pic into db
    photo_id = addPhotoToDB(sha1,fileType,dateTaken,args.privacy)

    # archive the photo
    archivedPhoto=archivePhoto(filename,sha1,fileType,localArchivePath,args,photo_id)

    # generate thumbnails
    thumbFilenames = util.genThumbnails(sha1,fileType,app.config,regen=args.regen)
    # send thumbnails to S3
    S3success = False
    if args.S3 == True:
      if checkImportStatusS3(photo_id) == False:
        for thumbFilename in thumbFilenames:
          S3success = aws.uploadToS3(localArchivePath+'/'+thumbFilename,thumbFilename,app.config,regen=args.regen,policy='public-read')

    # save import meta
    saveImportMeta(photo_id,filename,importSource=os.uname()[1],S3=S3success)

    # add tags
    if args.tags:
      tags = args.tags.split(',')
      for tag in tags:
        photosAddTag(photo_id,tag)

    # add dirtags
    if args.dirtags:
      ignoreTags=app.config['IGNORETAGS']
      dirTags(photo_id,filename,ignoreTags)

    # add parent dir tag
    if args.parentdirphotoset:
      parentDirPhotoSet(photo_id,filename)

    # add to photoset
    if args.photoset:
      photosetsAddPhoto(photoset_id,photo_id)

  # main
  logger.info('Import Finished')

if __name__ == "__main__":
  # set an app context so Flask g works #hack
  ctx = app.test_request_context()
  ctx.push()

  main()
  ctx.push()