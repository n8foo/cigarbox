#! /usr/bin/env python

# -*- coding: utf-8 -*-
"""
    CigarBox
    ~~~~~~

    A smokin' fast personal photostream

    :copyright: (c) 2015 by Nathan Hubbard @n8foo.
    :license: Apache, see LICENSE for more details.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import sqlite3, shutil, time, datetime
import util, aws
from db import *
from process import *

parser = argparse.ArgumentParser(description='import photos into photos system.')
parser.add_argument('--files', metavar='N', type=str, nargs='+',
                   help='files to import', required=True)
parser.add_argument('--tags', help='assign comma separated tag(s) to an import')
parser.add_argument('--dirtags', help='tag photos based on directory structure', action='store_true')
parser.add_argument('--photoset', help='add this import to a photoset')
parser.add_argument('--parentdirphotoset', help='assign a photoset name based on parent directory', action='store_true', default=False)
parser.add_argument('--regen', help='regenerate thumbnails', action='store_true', default=False)
parser.add_argument('--S3', help='upload to S3', action='store_true')
parser.add_argument('--privacy', help='set privacy on a photo, default is none/public', choices=['public','family','friends','private','disabled'])
parser.add_argument('--importsource', default=os.uname()[1], help='override import source')
args = parser.parse_args()

logger = util.setup_custom_logger('cigarbox')

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


def main():
  """Main program"""
  logger.info('Starting Import')
  if args.photoset:
    photoset_id = photosetsCreate(args.photoset)

  for filename in args.files:
    # log what we're doing
    logger.info('Processing file %s', filename)

    # set some variables
    dateTaken=getDateTaken(filename)
    fileType = getfileType(os.path.basename(filename))
    sha1=util.hashfile(filename)

    # insert pic into db
    photo_id = addPhotoToDB(sha1=sha1,fileType=fileType,dateTaken=dateTaken)

    # set photo privacy
    if args.privacy:
      setPhotoPrivacy(photo_id=photo_id,privacy=args.privacy)

    # archive the photo
    archivedPhoto=archivePhoto(filename,sha1,fileType,localArchivePath,args.S3,photo_id)

    # generate thumbnails
    thumbFilenames = util.genThumbnails(sha1,fileType,app.config,regen=args.regen)

    # send thumbnails to S3
    S3success = False
    if args.S3 == True:
      if checkImportStatusS3(photo_id) == False:
        for thumbFilename in thumbFilenames:
          # Make large sizes private (AI training protection)
          # _k (500px), _c (800px), _b (1024px) are valuable for AI training - keep private
          # _n (320px), _m (240px), _t (100px) are too small for quality training - keep public
          policy = 'private' if ('_b.jpg' in thumbFilename or '_c.jpg' in thumbFilename or '_k.jpg' in thumbFilename) else 'public-read'
          S3success = aws.uploadToS3(localArchivePath+'/'+thumbFilename,thumbFilename,app.config,regen=args.regen,policy=policy)

    # save import meta
    saveImportMeta(photo_id,filename,importSource=args.importsource,S3=S3success)

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