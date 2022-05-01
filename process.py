#! /usr/bin/env python

"""file processing methods"""

import os, sqlite3, shutil, time, datetime, logging
import util, aws
from db import *

from app import app


# set up logging
logger = logging.getLogger('cigarbox')


def photosetsCreate(title,description=None):
  """create a photoset - takes title and optional description. returns id"""
  try:
    photoset = Photoset.get(Photoset.title == title)
  except Photoset.DoesNotExist:
    logger.info('creating photoset: %s',title)
    photoset = Photoset.create(title=title,description=description)
  return photoset.id

def saveImportMeta(photo_id,filename,importSource,sha1,S3=False,clientfilename=None):
  importPath = os.path.abspath(filename)
  fileDate = time.ctime(os.path.getmtime(filename))
  try:
    meta = ImportMeta.get(ImportMeta.photo == photo_id)
  except ImportMeta.DoesNotExist:
    meta = ImportMeta.create(photo=photo_id,filedate=fileDate,importpath=clientfilename,importsource=importSource,s3=S3,sha1=sha1)
    logger.info('recording import meta for photo id: %s sha1: %s' % (photo_id,sha1))
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
  except Exception as e:
    return e

def getSha1FromPhotoID (photo_id):
  photo = Photo.get(Photo.id == photo_id)
  return(photo.sha1)

def getPhotoIDFromSha1 (sha1):
  photo = Photo.get(Photo.sha1 == sha1)
  return(photo.id)

def getOriginalPhotoName (photo_id):
  sha1 = getSha1FromPhotoID(photo_id)
  secret_key = app.config['SECRET_KEY']
  # some as yet undefined sorcery
  return(originalPhotoName)

def setPhotoPrivacy(photo_id,privacy):
  """set privacy"""
  privacyNum = app.config['PRIVACYFLAGS'][privacy]
  logger.info('privacy: %s for photo id: %s', privacy,photo_id)
  try:
    q = Photo.update(privacy=privacyNum).where(id == photo_id)
    q.execute()
    return True
  except Exception as e:
    return e


def addPhotoToDB(sha1,fileType,dateTaken):
  """adds photo to photos table, returns photo_id"""
  try:
    photo = Photo.get(Photo.sha1 == sha1)
    return photo.id
  except Photo.DoesNotExist:
    logger.info('Adding to DB: %s %s %s', sha1,fileType,dateTaken)
    photo = Photo.create(sha1=sha1,filetype=fileType,datetaken=dateTaken)
    return photo.id
  except Exception as e:
    return e

def replacePhoto(photo_id,sha1,fileType,dateTaken):
  """replaces a photo based on photo_id, returns new sha1"""
  try:
    logger.info('Replacing photo_id %s with %s %s', (photo_id,sha1,dateTaken))
    q = Photo.update(sha1=sha1,filetype=fileType,datetaken=dateTaken).where(id == photo_id)
    q.execute()
    return sha1
  except Exception as e:
    return e

def photosAddTag(photo_id,tag):
  """add tags to a photo: takes photo id and tag. normalizes tag. returns tag id"""
  normalizedtag = util.normalizeString(tag)
  # create the tag first
  try:
    tagobject = Tag.get(Tag.name == normalizedtag)
  except Tag.DoesNotExist:
    tagobject = Tag.create(name = normalizedtag)
    logger.info('created tag: {} id: '.format(tag,tagobject.id))
  except Exception as e:
    raise e
  # ok now we have the tag_id and photo_id, let's do this
  try:
    phototag = PhotoTag.get(PhotoTag.photo == photo_id,PhotoTag.tag == tagobject.id)
    return id
  except PhotoTag.DoesNotExist:
    logger.info('tagging photo id: {} tag: {}'.format(photo_id, tag))
    phototag = PhotoTag.create(photo=photo_id,tag=tagobject.id)
  except Exception as e:
    return e

def photosRemoveTag(photo_id,tag):
  """add tags to a photo: takes photo id and tag. normalizes tag. returns tag id"""
  normalizedtag = util.normalizeString(tag)
  # create the tag first
  try:
    deleteTag = Tag.get(Tag.name == normalizedtag)
  except Tag.DoesNotExist:
    response['text'] = 'Tag Does not Exist: {}'.format(normalizedtag)
  except Exception as e:
    raise e
  # ok now we have the tag_id (in deleteTag.id) and photo_id
  try:
    deletePhotoTag = PhotoTag.get(PhotoTag.photo == photo_id,PhotoTag.tag == deleteTag.id)
    deletePhotoTag = PhotoTag.delete().where(PhotoTag.id == deletePhotoTag.id)
    deletePhotoTag.execute()
  except PhotoTag.DoesNotExist:
    logger.info('Tag not associated with photo: {}'.format(normalizedtag))
    response['text'] = 'Tag not associated with photo: {}'.format(normalizedtag)
  except Exception as e:
    raise e
  return(photo_id,tag)


def getfileType(filename):
  fileType = filename.split('.')[-1].lower()
  return fileType

def archivePhoto(file,sha1,fileType,localArchivePath,uploadToS3,photo_id):
  """store the photo in the archive"""
  (sha1Path,sha1Filename)=util.getSha1Path(sha1)
  archivedPhoto='%s/%s/%s.%s' % (localArchivePath,sha1Path,sha1Filename,fileType)
  if not os.path.isdir(localArchivePath+'/'+sha1Path):
    os.makedirs(localArchivePath+'/'+sha1Path)
  if not os.path.isfile(archivedPhoto):
    try:
      logger.info('Copying %s -> %s',file,archivedPhoto)
      shutil.copy2(file,archivedPhoto)
    except Exception as e:
      raise e
  if uploadToS3 == True:
    if checkImportStatusS3(photo_id) == False:
      S3Key='%s/%s.%s' % (sha1Path,sha1Filename,fileType)
      aws.uploadToS3(file,S3Key,app.config,policy=app.config['AWSPOLICY'])
  return(archivedPhoto)

def dirTags(photo_id,file,ignoreTags):
  """add tags based on directory structure"""
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
  """add tags based on parent directory"""
  parentDir = os.path.dirname(file).split('/')[-1]
  photoset_id = photosetsCreate(parentDir)
  photosetsAddPhoto(photoset_id,photo_id)
  return True

def parentDirTags(file):
  """add tag based on parent directory"""
  parentDir = os.path.dirname(file).split('/')[-1]
  return parentDir

def getDateTaken(filename):
  """get a date from exif or file date"""
  try:
    exifDateTaken = util.getExifTags(filename)['DateTimeOriginal']
    dateTaken = datetime.datetime.strptime(exifDateTaken, "%Y:%m:%d %H:%M:%S" )
  except Exception as e:
    dateTaken = None
  return(dateTaken)