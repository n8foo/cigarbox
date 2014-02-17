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
parser.add_argument('--set', help='assign a set to an import set')
parser.add_argument('--gallery', help='assign a gallery to an import')
parser.add_argument('--tags', help='assign comma separated tag(s) to an import')
parser.add_argument('--dirtags', help='tag photos based on directory structure', action='store_true')
parser.add_argument('--photoset', help='add this import to a photoset')
parser.add_argument('--regen', help='regenerate thumbnails', action='store_true', default=False)
parser.add_argument('--S3', help='upload to S3', action='store_true', default=True)
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
  logger.info('creating photoset: %s', title)
  c.execute('SELECT id FROM photosets where title=?',(title,))
  photoset_id = c.fetchone()
  if photoset_id != None:
    return photoset_id[0]
  else:
    c.execute('INSERT INTO photosets VALUES(NULL, ?, ?, CURRENT_TIMESTAMP)',(title,description,))
    return c.lastrowid

def photosetsAddPhoto(photoset_id,photo_id):
  try:
    c.execute('INSERT INTO photosets_photos VALUES(NULL, ?, ?, CURRENT_TIMESTAMP)',(photoset_id,photo_id,))
    logger.info('adding photo id: %s to photoset id: %s',photo_id,photoset_id,)
  except Exception, e:
    return e


def addPhotoToDB(sha1,fileType,origFileName,dateTaken):
  logger.info('Adding to DB: %s %s %s %s', sha1,fileType,origFileName,dateTaken)
  c.execute ('SELECT id FROM photos where sha1 = ?',(sha1,))
  photo_id = c.fetchone()
  if photo_id != None:
    return photo_id[0]
  else: 
    c.execute('INSERT INTO photos VALUES(NULL, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)', (sha1, fileType, origFileName, dateTaken,))
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

def getfileType(origFileName):
  fileType = origFileName.split('.')[-1].lower()
  logger.info('File type: %s',fileType)
  return fileType

def archivePhoto(file,sha1,fileType,localArchivePath,args):
  (sha1Path,sha1FileName)=cigarbox.util.getSha1Path(sha1)
  archivedPhoto='%s/%s/%s.%s' % (localArchivePath,sha1Path,sha1FileName,fileType)
  logger.info('Copying %s -> %s',file,archivedPhoto)
  if not os.path.isdir(localArchivePath+'/'+sha1Path):
    os.makedirs(localArchivePath+'/'+sha1Path)
  if not os.path.isfile(archivedPhoto):
    try:
      shutil.copy2(file,archivedPhoto)
    except Exception, e:
      raise e
  if args.S3:
      S3Key='%s/%s.%s' % (sha1Path,sha1FileName,fileType)
      logger.info('Uploading %s -> %s',file,S3Key)
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
  return True

def importFile(filename):
  """import a file"""
  logger.info('Importing file %s', filename)
  exifTags = cigarbox.util.getExifTags(filename)
  if exifTags:
    if 'Image DateTime' in exifTags:
      dateTaken = str(exifTags['Image DateTime'])
    else:
      dateTaken = time.ctime(os.path.getmtime(filename))
  else:
    dateTaken = time.ctime(os.path.getmtime(filename))
  # set some variables
  origFileName = os.path.basename(filename)
  fileType = getfileType(origFileName)
  sha1=cigarbox.util.hashfile(filename)
  # insert pic into db
  photo_id = addPhotoToDB(sha1,fileType,origFileName,dateTaken)
  # archive the photo
  archivedPhoto=archivePhoto(filename,sha1,fileType,localArchivePath,args)
  # generate thumbnails
  cigarbox.util.genThumbnails(archivedPhoto,app.config,regen=args.regen)

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

