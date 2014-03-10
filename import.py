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
import cigarbox.util, cigarbox.aws

logger = cigarbox.util.setup_custom_logger('cigarbox')
logger.info('starting import....')

from flask import Flask, g
app = Flask(__name__)

# Load default config and override config from config file
app.config.from_object('config')

localArchivePath=app.config['LOCALARCHIVEPATH']

def connect_db():
  """Connects to the specific database."""
  rv = sqlite3.connect(app.config['DATABASE'])
  rv.row_factory = sqlite3.Row
  return rv

def init_db():
  """Creates the database tables."""
  cur = get_db()
  with app.open_resource('schema.sql', mode='r') as f:
      cur.cursor().executescript(f.read())
  cur.commit()

def query_db(query, args=(), one=False):
  cur = get_db().execute(query, args)
  rv = cur.fetchall()
  cur.close()
  return (rv[0] if rv else None) if one else rv

def insert_db(query, args=()):
  cur = get_db().execute(query, args)
  g._database.commit()
  id = cur.lastrowid
  cur.close()
  return id

def get_db():
  """Opens DB connection if it none exists"""
  db = getattr(g, '_database', None)
  if db is None:
      db = g._database = connect_db()
  return db

@app.teardown_appcontext
def teardown_db(exception):
  """Closes the database again at the end of the request."""
  db = getattr(g, '_database', None)
  if db is not None:
      db.close()

def photosetsCreate(title,description=None):
  """create a photoset - takes title and optional description. returns id"""
  result = query_db('SELECT id \
    FROM photosets \
    WHERE title=?',(title,),one=True)
  if result != None:
    return result['id']
  else:
    logger.info('creating photoset: %s', title)
    id = insert_db('INSERT INTO photosets \
      VALUES(NULL, ?, ?, CURRENT_TIMESTAMP)',(title,description,))
    return id

def saveImportMeta(photo_id,filename,importSource=args.importsource,S3=False):
  importPath = os.path.abspath(filename)
  fileDate = time.ctime(os.path.getmtime(filename))
  try:
    insert_db('INSERT INTO import_meta \
      VALUES(NULL, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)',(photo_id,fileDate,importPath,importSource,S3,))
    logger.info('recording import meta for photo id: %s',photo_id)
  except Exception, e:
    return e

def checkImportStatusS3(photo_id):
  result = query_db('SELECT S3 \
    FROM import_meta \
    WHERE photo_id = ?',(photo_id,))
  if result:
    if result[0]['S3'] == 1:
      return True
  else:
    return False

def photosetsAddPhoto(photoset_id,photo_id):
  try:
    insert_db('INSERT INTO photosets_photos \
      VALUES(NULL, ?, ?, CURRENT_TIMESTAMP)',(photoset_id,photo_id,))
    logger.info('adding photo id: %s to photoset id: %s',photo_id,photoset_id,)
  except Exception, e:
    return e

def getSha1FromPhotoID (photo_id):
  sha1 = query_db('SELECT sha1 FROM photos where id = ?',(photo_id,), one=True)
  return(sha1)

def getOriginalPhotoName (photo_id):
  sha1 = getSha1FromPhotoID(photo_id)
  secret_key = app.config['SECRET_KEY']
  # some as yet undefined sorcery
  return(originalPhotoName)


def addPhotoToDB(sha1,fileType,dateTaken,privacy):
  """adds photo to photos table, returns photo_id"""
  # set privacy
  privacyNum = app.config['PRIVACYFLAGS'][privacy]
  result = query_db('SELECT id \
    FROM photos \
    WHERE sha1 = ?',(sha1,),one=True)
  if result != None:
    return result['id']
  else:
    logger.info('Adding to DB: %s %s %s %s', sha1,fileType,dateTaken,privacy)
    id = insert_db('INSERT INTO photos \
      VALUES(NULL, ?, ?, ?, ?, CURRENT_TIMESTAMP)', (privacyNum,sha1,fileType,dateTaken))
    return id

def photosAddTag(photo_id,tag):
  """add tags to a photo: takes photo id and tag. normalizes tag. returns tag id"""
  tag = cigarbox.util.normalizeString(tag)
  result = query_db('SELECT id \
    FROM tags \
    WHERE tag=?',(tag,),one=True)
  if result == None:
    try: 
      tag_id = insert_db('INSERT INTO tags \
        VALUES(NULL, ?, CURRENT_TIMESTAMP)',(tag,))
    except Exception as e:
      raise e
  else:
    tag_id = result['id']
  # ok now we have the tag_id and photo_id, let's do this
  try:
    id = insert_db('INSERT INTO tags_photos VALUES(NULL, ?, ?, CURRENT_TIMESTAMP)',(tag_id, photo_id))
    logger.info('tagging photo id %s tag: %s', photo_id, tag)
    return id
  except Exception, e:
    return e

def getfileType(filename):
  fileType = filename.split('.')[-1].lower()
  return fileType

def archivePhoto(file,sha1,fileType,localArchivePath,args,photo_id):
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
    if checkImportStatusS3(photo_id) == False:
      S3Key='%s/%s.%s' % (sha1Path,sha1Filename,fileType)
      cigarbox.aws.uploadToS3(file,S3Key,app.config,policy=app.config['AWSPOLICY'])
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
      exifDateTaken = cigarbox.util.getExifTags(filename)['DateTimeOriginal']
      dateTaken = datetime.datetime.strptime(exifDateTaken, "%Y:%m:%d %H:%M:%S" )
    except Exception, e:
      dateTaken = None

    # set some variables
    fileType = getfileType(os.path.basename(filename))
    sha1=cigarbox.util.hashfile(filename)

    # insert pic into db
    photo_id = addPhotoToDB(sha1,fileType,dateTaken,args.privacy)

    # archive the photo
    archivedPhoto=archivePhoto(filename,sha1,fileType,localArchivePath,args,photo_id)

    # generate thumbnails
    thumbFilenames = cigarbox.util.genThumbnails(sha1,fileType,app.config,regen=args.regen)
    # send thumbnails to S3
    S3success = False
    if args.S3 == True:
      if checkImportStatusS3(photo_id) == False:
        for thumbFilename in thumbFilenames:
          S3success = cigarbox.aws.uploadToS3(localArchivePath+'/'+thumbFilename,thumbFilename,app.config,regen=args.regen,policy='public-read')

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