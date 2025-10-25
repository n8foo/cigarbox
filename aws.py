#! /usr/bin/env python

"""aws methods"""

# std libs
import sys, logging

# third party
import boto

# set up logging
logger = logging.getLogger('cigarbox')

def createS3Bucket(config):
  bucket_name = config['S3_BUCKET_NAME']
  conn = boto.connect_s3(config['AWS_ACCESS_KEY_ID'],config['AWS_SECRET_ACCESS_KEY'])
  bucket = conn.create_bucket(bucket_name,location=boto.s3.connection.Location.DEFAULT)


def uploadToS3(localfile,S3Key,config,regen=False,policy='private'):
  bucket_name = config['S3_BUCKET_NAME']
  logger.info('S3 Upload Starting: local=%s -> s3://%s/%s (policy=%s, replace=%s)',
              localfile, bucket_name, S3Key, policy, regen)

  # Check if local file exists
  import os
  if not os.path.exists(localfile):
    logger.error('S3 Upload FAILED: Local file does not exist: %s', localfile)
    return False

  file_size = os.path.getsize(localfile)
  logger.info('S3 Upload: File size: %d bytes', file_size)

  try:
    conn = boto.connect_s3(config['AWS_ACCESS_KEY_ID'],config['AWS_SECRET_ACCESS_KEY'])
    logger.info('S3 Upload: Connected to S3')
  except Exception as e:
    logger.error('S3 Upload FAILED: Could not connect to S3: %s', str(e))
    return False

  try:
    bucket = conn.get_bucket(bucket_name)
    logger.info('S3 Upload: Got bucket: %s', bucket_name)
  except Exception as e:
    logger.error('S3 Upload FAILED: Could not get bucket %s: %s', bucket_name, str(e))
    return False

  from boto.s3.key import Key
  k = Key(bucket)
  k.key = S3Key
  try:
     k.set_contents_from_filename(localfile, replace=regen, policy=policy)
     logger.info('S3 Upload SUCCESS: %s uploaded to s3://%s/%s', localfile, bucket_name, S3Key)
     return True
  except Exception as e:
     logger.error('S3 Upload FAILED: Error uploading %s to %s: %s', localfile, S3Key, str(e))
     return False 

def deleteFromS3(S3Key,config):
  bucket_name = config['S3_BUCKET_NAME']
  conn = boto.connect_s3(config['AWS_ACCESS_KEY_ID'],config['AWS_SECRET_ACCESS_KEY'])
  bucket = conn.get_bucket(bucket_name)
  logger.info('Deleting from S3: %s' % (S3Key))
  from boto.s3.key import Key
  k = Key(bucket)
  k.key = '/' + S3Key
  try:
     k.delete()
     return True
  except Exception as e:
     return False 

def getPrivateURL(config,S3Key):
  bucket_name = config['S3_BUCKET_NAME']
  conn = boto.connect_s3(config['AWS_ACCESS_KEY_ID'],config['AWS_SECRET_ACCESS_KEY'])

  bucket = conn.get_bucket(bucket_name)
  from boto.s3.key import Key
  k = Key(bucket)
  k.key = S3Key
  try:
    url = k.generate_url(10)
    return url
  except Exception as e:
    return None