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
parser.add_argument('--tags', help='assign tag(s) to an import')
parser.add_argument('--dirtags', help='tag photos based on directory structure', action='store_true')
parser.add_argument('--photoset', help='add this import to a photoset')
parser.add_argument('--regen', help='regenerate thumbnails', action='store_true')
args = parser.parse_args()


ignoreTags = ['Users','nathan','Pictures','www_pics']

import os, sqlite3, shutil, time, logging, hashlib
import cigarbox.util

from flask import Flask
app = Flask(__name__)

# Load default config and override config from config file
app.config.from_object('config')


localArchivePath=app.config['LOCALARCHIVEPATH']


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

def hashfile(file):
  BLOCKSIZE = 65536
  sha1 = hashlib.sha1()
  with open(file, 'rb') as afile:
    buf = afile.read(BLOCKSIZE)
    while len(buf) > 0:
        sha1.update(buf)
        buf = afile.read(BLOCKSIZE)
  return(sha1.hexdigest())

def photosetsCreate(title,description=None):
  logging.info('creating photoset: %s', title)
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
    logging.info('adding photo id: %s to photoset id: %s',photo_id,photoset_id,)
  except Exception, e:
    return e


def addPhoto(sha1,fileType,origFileName,dateTaken):
  logging.info('Adding to DB: %s %s %s %s', sha1,fileType,origFileName,dateTaken)
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
    logging.info('tagging photo id %s tag: %s', photo_id, tag)
    return c.lastrowid
  except Exception, e:
    return e

def getfileType(origFileName):
  fileType = origFileName.split('.')[-1].lower()
  logging.info('File type: %s',fileType)
  return fileType

def archivePhoto(file,sha1,fileType,localArchivePath):
  sha1Path=cigarbox.util.getSha1Path(sha1)
  logging.info('Copying %s -> %s/%s/%s.%s',file,localArchivePath,sha1Path,sha1,fileType)
  if not os.path.isdir(localArchivePath+'/'+sha1Path):
    os.makedirs(localArchivePath+'/'+sha1Path)
  try:
      shutil.copy2(file,localArchivePath+'/'+sha1Path+'/'+sha1+'.'+fileType)
  except Exception, e:
    raise
  return(localArchivePath+'/'+sha1Path+'/'+sha1+'.'+fileType)

def dirTags(photo_id,file):
  # tag based on directory structure
  osPathDirnames = os.path.dirname(file).split('/')
  dirTags = []
  for osPathDirname in osPathDirnames:
    tag = str(osPathDirname)
    if tag != '':
      if tag not in ignoreTags:
        dirTags.append(tag)
        photosAddTag(photo_id,tag)
  return True

def importFile(file,photoset=None):
  logging.info('Importing file %s', file)
  f = open(file, 'rb')
  exifTags = cigarbox.util.getExifTags(f)
  if exifTags:
    if 'Image DateTime' in exifTags:
      dateTaken = str(exifTags['Image DateTime'])
    else:
      dateTaken = time.ctime(os.path.getmtime(file))
  else:
    dateTaken = time.ctime(os.path.getmtime(file))

  origFileName = os.path.basename(file)
  fileType = getfileType(origFileName)
  sha1=hashfile(file)
  archivedPhoto=archivePhoto(file,sha1,fileType,localArchivePath)

  cigarbox.util.genThumbnails(archivedPhoto,regen=args.regen)
  # insert pic into db
  photo_id = addPhoto(sha1,fileType,origFileName,dateTaken)
  dirTags(photo_id,file)

  if args.tags != None:
    tags = args.tags.split(',')
    for tag in tags:
      photosAddTag(photo_id,tag)

  # close file
  f.close()
  # add to photoset
  photosetsAddPhoto(photoset_id,photo_id)



# the meat

conn = sqlite3.connect('photos.db')
c = conn.cursor()

photoset_id = None
if args.photoset != None:
  photoset_id = photosetsCreate(args.photoset)

for file in args.files:
  importFile(file,photoset_id)



conn.commit()
conn.close()

def main():
  # main
  print 'done'

if __name__ == "__main__":
    main()

