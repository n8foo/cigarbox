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
parser.add_argument('--S3', help='upload to S3', action='store_true', default=False)
parser.add_argument('--importsource', help='override import source')
args = parser.parse_args()


import os, sqlite3, shutil, time
import cigarbox.util, cigarbox.aws

logger = cigarbox.util.setup_custom_logger('cigarbox')
logger.info('starting import....')

from flask import Flask
app = Flask(__name__)

# Load default config and override config from config file
app.config.from_object('config')


localArchivePath=app.config['LOCALARCHIVEPATH']

def photosetsCreate(title,description=None):
  c.execute('SELECT id FROM photosets where title=?',(title,))
  photoset_id = c.fetchone()
  if photoset_id != None:
    return photoset_id[0]
  else:
    logger.info('creating photoset: %s', title)
    c.execute('INSERT INTO photosets VALUES(NULL, ?, ?, CURRENT_TIMESTAMP)',(title,description,))
    return c.lastrowid

def saveImportMeta(photo_id,importPath,importSource=args.importsource,S3=False):
  importPath = os.path.abspath(filename)
  try:
    c.execute('INSERT INTO import_meta VALUES(NULL, ?, ?, ?, ?, CURRENT_TIMESTAMP)',(photo_id,importPath,importSource,S3,))
    logger.info('adding photo id: %s to import meta',photo_id)
  except Exception, e:
    return e
def checkImportStatusS3(photo_id):
  get_db()
  try:
    c.execute('SELECT S3 FROM import_meta WHERE photo_id = ?',(photo_id,))
    status = c.fetchone()
  except Exception, e:
    return e
  return status

def photosetsAddPhoto(photoset_id,photo_id):
  try:
    c.execute('INSERT INTO photosets_photos VALUES(NULL, ?, ?, CURRENT_TIMESTAMP)',(photoset_id,photo_id,))
    logger.info('adding photo id: %s to photoset id: %s',photo_id,photoset_id,)
  except Exception, e:
    return e

def getSha1FromPhotoID (photo_id):
  c.execute ('SELECT sha1 FROM photos where id = ?',(photo_id,))
  sha1 = c.fetchone()
  return(sha1)

def getOriginalPhotoName (photo_id):
  sha1 = getSha1FromPhotoID(photo_id)
  secret_key = app.config['SECRET_KEY']
  # some as yet undefined sorcery
  return(originalPhotoName)


def addPhotoToDB(sha1,fileType,origFilename,dateTaken):
  """adds photo to photos table"""
  c.execute ('SELECT id FROM photos where sha1 = ?',(sha1,))
  photo_id = c.fetchone()
  if photo_id != None:
    return photo_id[0]
  else:
    logger.info('Adding to DB: %s %s %s %s', sha1,fileType,origFilename,dateTaken)
    c.execute('INSERT INTO photos VALUES(NULL, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)', (sha1, fileType, origFilename, dateTaken,))
    return c.lastrowid

def photosAddTag(photo_id,tag):
  tag = cigarbox.util.normalizeString(tag)
  c.execute ('SELECT id FROM tags WHERE tag=?',(tag,))
  tag_id = c.fetchone()
  if tag_id == None:
    try: 
      c.execute('INSERT INTO tags VALUES(NULL, ?, CURRENT_TIMESTAMP)',(tag,))
      tag_id = c.lastrowid
    except Exception as e:
      # Roll back any change if something goes wrong
      conn.rollback()
      raise e
  else:
    tag_id = tag_id[0]
  # ok now we have the tag_id and photo_id, let's do this
  try:
    c.execute('INSERT INTO tags_photos VALUES(NULL, ?, ?, CURRENT_TIMESTAMP)',(tag_id, photo_id))
    logger.info('tagging photo id %s tag: %s', photo_id, tag)
    return c.lastrowid
  except Exception, e:
    return e

def getfileType(origFilename):
  fileType = origFilename.split('.')[-1].lower()
  return fileType

def archivePhoto(file,sha1,fileType,localArchivePath,args):
  (sha1Path,sha1Filename)=cigarbox.util.getSha1Path(sha1)
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
      S3Key='%s/%s.%s' % (sha1Path,sha1Filename,fileType)
      cigarbox.aws.uploadToS3(file,S3Key,app.config)

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

def importFile(filename):
  """import a file"""
  logger.info('Analyzing file %s', filename)
  exifTags = cigarbox.util.getExifTags(filename)
  if exifTags:
    if 'Image DateTime' in exifTags:
      dateTaken = str(exifTags['Image DateTime'])
    else:
      dateTaken = time.ctime(os.path.getmtime(filename))
  else:
    dateTaken = time.ctime(os.path.getmtime(filename))
  # set some variables
  origFilename = os.path.basename(filename)
  fileType = getfileType(origFilename)
  sha1=cigarbox.util.hashfile(filename)
  # insert pic into db
  photo_id = addPhotoToDB(sha1,fileType,origFilename,dateTaken)
  # archive the photo
  archivedPhoto=archivePhoto(filename,sha1,fileType,localArchivePath,args)
  # generate thumbnails
  thumbFilenames = cigarbox.util.genThumbnails(sha1,fileType,app.config,regen=args.regen)
  # send thumbnails to S3
  S3success = False
  if args.S3 == True:
    for thumbFilename in thumbFilenames:
      S3success = cigarbox.aws.uploadToS3(app.config['LOCALARCHIVEPATH']+'/'+thumbFilename,thumbFilename,app.config,regen=args.regen)

  saveImportMeta(photo_id,filename,importSource=os.uname()[1],S3=S3success)
  return photo_id


# the meat

conn = sqlite3.connect('photos.db')
c = conn.cursor()

if args.photoset:
  photoset_id = photosetsCreate(args.photoset)

for filename in args.files:
  # import the file
  photo_id = importFile(filename)
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
  conn.commit()

conn.close()

def main():
  # main
  print 'done'

if __name__ == "__main__":
    main()

