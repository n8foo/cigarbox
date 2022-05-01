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
parser.add_argument('--dirtag', help='auto tag photos based on parent directory. Note: overrides tags', action='store_true')
parser.add_argument('--photoset', help='add this import to a photoset')
parser.add_argument('--privacy', help='set privacy on a photo, default is none/public', choices=['public','family','friends','private','disabled'], default='public')
parser.add_argument('--importsource', default=os.uname()[1], help='override import source')
parser.add_argument('--apiurl', help='URL of the cigarbox API endpoint', default='http://127.0.0.1:9601/api')
parser.add_argument('--dryrun', action='store_true', help='show what would have been done')
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
    logger.info('filename:{0}'.format(filename))

    # get sha1 to also send for verification
    sha1=util.hashfile(filename)

    # check if it exists already via api, if so, skip it
    if check_exists(sha1):
      logger.info('File already uploaded!')
      # but because we want to update tags anyway, update them
      if args.tags:
        resp = get_photo_id_from_sha1(sha1)
        add_tags(resp['photo_id'], args.tags)
      continue

    # set up tempfilename
    tempname=ts+'_'+os.path.basename(filename)
    logger.info("tempname:{0}".format(tempname))


    # start setting up the data to send
    fields={'files': (tempname, open(filename, 'rb') ) }
    fields['sha1'] = sha1
    fields['clientfilename'] = filename
    if args.tags:
      fields['tags'] = args.tags
    if args.photoset:
      fields['photoset'] = args.photoset
    if args.tags:
      fields['tags'] = args.tags
    if args.privacy:
      fields['privacy'] = args.privacy
    # add dirtag
    if args.dirtag:
      dirtag = parentDirTags(filename)
      fields['tags'] = dirtag
      logger.info('image tagged from parent directory:{0}'.format(dirtag))

    # dry run exits loop here
    if args.dryrun:
      logger.info('{0} finished! ({1} {2})'.format(filename, '200', 'dryrun'))
      continue


    m = MultipartEncoder(fields=fields)
    try:
      r = requests.post('{0}/upload'.format(args.apiurl), data=m,headers={'Content-Type': m.content_type})
    except Exception as e:
      raise e
    else:
      logger.info('{0} finished! ({1} {2})'.format(filename, r.status_code, r.reason))
    photo_ids.add(r.json()['photo_ids'][0])
  photo_ids=list(photo_ids)
  return photo_ids


def check_exists(sha1):
  url = '{0}/sha1/{1}'.format(args.apiurl,sha1)

  resp = requests.get(url)
  data = resp.json()
  if data['exists'] == True:
    return True
  else:
    return False

def get_photo_id_from_sha1(sha1):
  url = '{0}/sha1/{1}'.format(args.apiurl,sha1)

  resp = requests.get(url)
  data = resp.json()
  return data


def add_tags(photo_id,tags):
  url = '{0}/photos/addtags'.format(args.apiurl)
  payload = dict(
    photo_id = photo_id,
    tags = tags
    )

  resp = requests.post(url=url, json=payload)
  logger.debug('{} {}'.format(url,payload))
  data = resp.json()



def main():
  """Main program"""
  logger.info('Starting Upload')

  photo_ids=uploadFiles(args.files)

  # main
  logger.info('Imported: '+', '.join(map(str, photo_ids)))
  logger.info('Upload Finished')

if __name__ == "__main__":
  # set an app context so Flask g works #hack
  ctx = app.test_request_context()
  ctx.push()

  main()
  ctx.push()