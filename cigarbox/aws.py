#! /usr/bin/env python

"""aws methods"""

# std libs
import sys, logging

# third party
import boto

# set up logging
logger = logging.getLogger('cigarbox')


def uploadToS3(localfile,S3Key,config,regen=False):
  bucket_name = config['S3_BUCKET_NAME']
  conn = boto.connect_s3(config['AWS_ACCESS_KEY_ID'],config['AWS_SECRET_ACCESS_KEY'])

  bucket = conn.create_bucket(bucket_name,
        location=boto.s3.connection.Location.DEFAULT)

  def percent_cb(complete, total):
      sys.stdout.write('.')
      sys.stdout.flush()
  logger.info('Syncing to S3: %s -> %s' % (localfile,S3Key))
  from boto.s3.key import Key
  k = Key(bucket)
  k.key = S3Key
  try:
     k.set_contents_from_filename(localfile, replace=regen, policy='public-read')
     return True
  except Exception, e:
     return False 
  
