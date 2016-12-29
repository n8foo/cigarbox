#! /usr/bin/env python

# -*- coding: utf-8 -*-
"""
    CigarBox
    ~~~~~~

    A smokin' fast personal photostream

    :copyright: (c) 2015 by Nathan Hubbard @n8foo.
    :license: Apache, see LICENSE for more details.
"""

import argparse
import os, sqlite3, shutil, time, datetime
import util, aws
from db import *
from process import *
from requests_toolbelt import MultipartEncoder
import requests

ts=str(int(time.time()))

parser = argparse.ArgumentParser(description='upload photos into photos system.')
parser.add_argument('--files', metavar='N', type=str, nargs='+',
                   help='files to import', required=True)
parser.add_argument('--tags', help='assign comma separated tag(s) to an import')
parser.add_argument('--dirtags', help='tag photos based on directory structure', action='store_true')
parser.add_argument('--showdirtags', help='show tags based on directory structure', action='store_true')
parser.add_argument('--photoset', help='add this import to a photoset')
parser.add_argument('--parentdirphotoset', help='assign a photoset name based on parent directory', action='store_true', default=False)
parser.add_argument('--privacy', help='set privacy on a photo, default is none/public', choices=['public','family','friends','private','disabled'], default='public')
parser.add_argument('--importsource', default=os.uname()[1], help='override import source')
parser.add_argument('--apiurl', help='URL of the cigarbox API endpoint', default='http://127.0.0.1:9001/api')
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


def uploadFiles(filenames):
  photo_ids=set()
  for filename in filenames:
    tempname=ts+'_'+os.path.basename(filename)
    logger.info(tempname)
    # get sha1 to also send for verification
    sha1=util.hashfile(filename)
    fields={'files': (tempname, open(filename, 'rb') ) }
    fields['sha1'] = sha1
    if args.tags:
      fields['tags'] = args.tags
    if args.photoset:
      fields['photoset'] = args.photoset
    if args.tags:
      fields['tags'] = args.tags
    if args.privacy:
      fields['privacy'] = args.privacy
    m = MultipartEncoder(fields=fields)
    try:
      r = requests.post('%s/upload' % args.apiurl, data=m,headers={'Content-Type': m.content_type})
    except Exception, e:
      raise e
    else:
      logger.info(filename+' -> '+tempname+' finished! ({0} {1})'.format(r.status_code, r.reason))
    photo_ids.add(r.json()['photo_ids'][0])
  photo_ids=list(photo_ids)
  logger.info(photo_ids)
  return photo_ids


def main():
  """Main program"""
  logger.info('Starting Upload')
  #if args.photoset:
  #  photoset_id = photosetsCreate(args.photoset)

  photo_ids=uploadFiles(args.files)


#    # add tags
#    if args.tags:
#      tags = args.tags.split(',')
#      for tag in tags:
#        photosAddTag(photo_id,tag)#

#    # add dirtags
#    if args.dirtags:
#      ignoreTags=app.config['IGNORETAGS']
#      dirTags(photo_id,filename,ignoreTags)#

#    # add parent dir tag
#    if args.parentdirphotoset:
#      parentDirPhotoSet(photo_id,filename)#

#    # add to photoset
#    if args.photoset:
#      photosetsAddPhoto(photoset_id,photo_id)

  # main
  logger.info('Imported: '+', '.join(map(str, photo_ids)))
  logger.info('Upload Finished')

if __name__ == "__main__":
  # set an app context so Flask g works #hack
  ctx = app.test_request_context()
  ctx.push()

  main()
  ctx.push()