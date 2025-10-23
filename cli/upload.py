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
import util
from requests_toolbelt import MultipartEncoder
import requests

ts=str(int(time.time()))

# Rate limiting - delay between API calls to avoid overwhelming server
API_CALL_DELAY = 0.1  # 100ms between requests

parser = argparse.ArgumentParser(description='upload photos into photos system.')
parser.add_argument('--files', metavar='N', type=str, nargs='+',
                   help='files to import', required=True)
parser.add_argument('--tags', help='assign comma separated tag(s) to an import')
parser.add_argument('--dirtag', help='auto tag photos based on parent directory. Note: overrides tags', action='store_true')
parser.add_argument('--photoset', help='add this import to a photoset')
parser.add_argument('--privacy', help='set privacy on a photo, default is none/public', choices=['public','family','friends','private','disabled'], default='public')
parser.add_argument('--importsource', default=os.uname()[1], help='override import source')
parser.add_argument('--apiurl', help='URL of the cigarbox API endpoint', default='http://127.0.0.1:9601/api')
parser.add_argument('--apikey', help='API key for authentication (or set CIGARBOX_API_KEY env var)')
parser.add_argument('--dryrun', action='store_true', help='show what would have been done')
parser.add_argument('--delay', type=float, default=0.1, help='delay between API calls in seconds (default: 0.1)')

# Only parse args when running as main, not when importing for tests
args = None

logger = util.setup_custom_logger('cigarbox')

from flask import Flask, g
app = Flask(__name__)

# Load default config and override config from config file
app.config.from_object('config')

localArchivePath=app.config['LOCALARCHIVEPATH']

def get_api_key():
  """Get API key from args or environment"""
  if args.apikey:
    return args.apikey
  return os.environ.get('CIGARBOX_API_KEY')

def uploadFiles(filenames):
  # set up data to return
  response={}

  # Get API key
  api_key = get_api_key()
  if not api_key:
    logger.error('API key required. Provide via --apikey or CIGARBOX_API_KEY environment variable')
    sys.exit(1)

  photo_ids=set()
  for filename in filenames:
    logger.info('filename:{0}'.format(filename))

    # Rate limiting - small delay between files to avoid 503
    if args.delay > 0:
      time.sleep(args.delay)

    # fields for the POST later
    fields={}

    # get sha1 to also send for verification
    sha1=util.hashfile(filename)

    # check if it exists already via api, if so, skip the file upload
    # and only send the photo_id and other fields
    exists=check_exists(sha1)
    if exists:
      # ok it exists, what's the photo id
      resp = get_photo_id_from_sha1(sha1)
      if resp and 'photo_id' in resp:
        photo_id=resp['photo_id']
        logger.info('Already uploaded as photo_id: {}'.format(photo_id))
        photo_ids.add(photo_id)
        fields['photo_id'] = photo_id
        # exit the loop for this file
      else:
        logger.warning('Could not get photo_id, will re-upload file')
        exists = False

    if not exists:
      # set up tempfilename
      tempname=ts+'_'+os.path.basename(filename)
      logger.info("tempname:{0}".format(tempname))
      fields={'files': (tempname, open(filename, 'rb') ) }

    # start setting up the data to send
    fields['sha1'] = sha1
    fields['clientfilename'] = filename
    fields['api_key'] = api_key
    # move to using tags API call
    if args.tags:
       fields['tags'] = args.tags
    if args.photoset:
      fields['photoset'] = args.photoset
    if args.privacy:
      fields['privacy'] = args.privacy
    #add dirtag
    if args.dirtag:
      # grab parent dir
      dirtag = parentDirTags(filename)
      fields['tags'] = dirtag
      logger.info('tagged from parent directory:{0}'.format(dirtag))

    #print(fields)

    # dry run exits loop here
    if args.dryrun:
      logger.info('{0} finished! ({1} {2})'.format(filename, '200', 'dryrun'))
      continue

    # set up the POST with fields
    m = MultipartEncoder(fields=fields)
    try:
      r = requests.post('{0}/upload'.format(args.apiurl), data=m,headers={'Content-Type': m.content_type})
    except Exception as e:
      logger.error('Failed to upload {}: {}'.format(filename, e))
      continue

    # Check for HTTP errors
    if r.status_code != 200:
      logger.error('{0} failed! ({1} {2})'.format(filename, r.status_code, r.reason))
      try:
        error_data = r.json()
        if 'error' in error_data:
          logger.error('  Error: {}'.format(error_data['error']))
        if 'message' in error_data:
          logger.error('  Message: {}'.format(error_data['message']))
      except:
        logger.error('  Response: {}'.format(r.text[:200]))
      continue

    logger.info('{0} finished! ({1} {2})'.format(filename, r.status_code, r.reason))

    # Parse response
    try:
      response_data = r.json()
      if 'photo_ids' in response_data and response_data['photo_ids']:
        photo_ids.add(response_data['photo_ids'][0])
    except Exception as e:
      logger.warning('Could not parse response for {}: {}'.format(filename, e))


    # if args.photoset:
    #   fields['photoset'] = args.photoset

  photo_ids=list(photo_ids)

  if not photo_ids:
    logger.warning('No photos were successfully uploaded!')

  return photo_ids

def parentDirTags(file):
  """add tag based on parent directory"""
  parentDir = os.path.dirname(file).split('/')[-1]
  return parentDir


def check_exists(sha1):
  url = '{0}/sha1/{1}'.format(args.apiurl,sha1)

  # Note: sha1 lookup endpoint doesn't require auth (read-only)
  try:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data['exists'] == True:
      return True
    else:
      return False
  except requests.exceptions.RequestException as e:
    logger.warning('Error checking if photo exists: {}'.format(e))
    # Assume it doesn't exist and continue with upload
    return False
  except ValueError as e:
    logger.warning('Invalid JSON response from server: {}'.format(e))
    return False

def get_photo_id_from_sha1(sha1):
  url = '{0}/sha1/{1}'.format(args.apiurl,sha1)

  try:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data
  except requests.exceptions.RequestException as e:
    logger.error('Error getting photo_id from sha1: {}'.format(e))
    return None
  except ValueError as e:
    logger.error('Invalid JSON response from server: {}'.format(e))
    return None


def api_add_tags(photo_id,tags):
  url = '{0}/photos/addtags'.format(args.apiurl)
  payload = dict(
    photo_id = photo_id,
    tags = tags
    )

  resp = requests.post(url=url, json=payload)
  logger.debug('{} {}'.format(url,payload))
  data = resp.json()
  return data

def api_add_photoset(photo_id,photoset):
  url = '{0}/photoset/addphoto'.format(args.apiurl)
  payload = dict(
    photo_id = photo_id,
    photoset = photoset
    )

  resp = requests.post(url=url, json=payload)
  logger.debug('{} {}'.format(url,payload))
  data = resp.json()
  return data

def main():
  """Main program"""
  logger.info('Starting Upload')

  photo_ids=uploadFiles(args.files)

  # for photo_id in photo_ids:
  # # run thru the various args and hit the API's directly
  #   if args.tags:
  #     api_add_tags(photo_id, args.tags)
  #     logger.info('photo_id: {} tagged: {}'.format(photo_id,args.tags))
  #   # if args.dirtag:
  #   #   # grab parent dir
  #   #   dirtag = parentDirTags(filename)
  #   #   api_add_tags(photo_id, dirtag)
  #   #   logger.info('tagged from parent directory:{0}'.format(dirtag))
  #   # api call for photoset
  #   if args.photoset:
  #     api_add_photoset(photo_id, args.photoset)
  #     logger.info('photo_id: {} gets photoset: "{}"'.format(photo_id,args.photoset))


  # main
  logger.info('Imported: '+', '.join(map(str, photo_ids)))
  logger.info('Upload Finished')

if __name__ == "__main__":
  # Parse command line arguments
  args = parser.parse_args()

  # set an app context so Flask g works #hack
  ctx = app.test_request_context()
  ctx.push()

  main()
  ctx.push()