#! /usr/bin/env python

"""aws methods"""

# std libs
import sys

# third party
import boto


def uploadToS3(localfile,s3Key,config,replace=False):
  bucket_name = config['S3_BUCKET_NAME']
  conn = boto.connect_s3(config['AWS_ACCESS_KEY_ID'],config['AWS_SECRET_ACCESS_KEY'])

  bucket = conn.create_bucket(bucket_name,
        location=boto.s3.connection.Location.DEFAULT)

  def percent_cb(complete, total):
      sys.stdout.write('.')
      sys.stdout.flush()

  from boto.s3.key import Key
  k = Key(bucket)
  k.key = s3Key
  k.set_contents_from_filename(localfile,cb=percent_cb, num_cb=10, replace=replace, policy='public-read')
