#! /usr/bin/env python

"""aws methods - boto3 version with connection caching"""

# std libs
import sys, logging, os

# third party
import boto3
from botocore.exceptions import ClientError

# set up logging
logger = logging.getLogger('cigarbox')

# Module-level S3 client cache (boto3 has built-in connection pooling)
_s3_client = None

def get_s3_client(config):
  """Get or create cached S3 client (boto3 handles connection pooling)"""
  global _s3_client
  if _s3_client is None:
    _s3_client = boto3.client(
      's3',
      aws_access_key_id=config['AWS_ACCESS_KEY_ID'],
      aws_secret_access_key=config['AWS_SECRET_ACCESS_KEY']
    )
    logger.debug('S3 client initialized')
  return _s3_client

def createS3Bucket(config):
  """Create S3 bucket (rarely used)"""
  bucket_name = config['S3_BUCKET_NAME']
  s3 = get_s3_client(config)
  try:
    s3.create_bucket(Bucket=bucket_name)
    logger.info('S3 bucket created: %s', bucket_name)
    return True
  except ClientError as e:
    logger.error('S3 bucket creation failed: %s', str(e))
    return False

def uploadToS3(localfile, S3Key, config, regen=False, policy='private'):
  """
  Upload file to S3 with specified ACL policy

  Args:
    localfile: Local file path
    S3Key: S3 object key (path in bucket)
    config: App config with AWS credentials and bucket name
    regen: If True, overwrite existing file (ignored - always overwrites)
    policy: ACL policy ('private' or 'public-read')

  Returns:
    True on success, False on failure
  """
  bucket_name = config['S3_BUCKET_NAME']
  logger.info('S3 Upload Starting: local=%s -> s3://%s/%s (policy=%s, replace=%s)',
              localfile, bucket_name, S3Key, policy, regen)

  # Check if local file exists
  if not os.path.exists(localfile):
    logger.error('S3 Upload FAILED: Local file does not exist: %s', localfile)
    return False

  file_size = os.path.getsize(localfile)
  logger.info('S3 Upload: File size: %d bytes', file_size)

  try:
    s3 = get_s3_client(config)

    # Detect Content-Type from file extension so browsers display inline (not download)
    import mimetypes
    content_type, _ = mimetypes.guess_type(localfile)
    if not content_type:
      content_type = 'application/octet-stream'  # Fallback

    # Map ACL policy and Content-Type
    extra_args = {
      'ACL': policy,
      'ContentType': content_type
    }

    # Upload file
    s3.upload_file(localfile, bucket_name, S3Key, ExtraArgs=extra_args)
    logger.info('S3 Upload SUCCESS: %s uploaded to s3://%s/%s (Content-Type: %s)',
                localfile, bucket_name, S3Key, content_type)
    return True

  except ClientError as e:
    logger.error('S3 Upload FAILED: Error uploading %s to %s: %s', localfile, S3Key, str(e))
    return False
  except Exception as e:
    logger.error('S3 Upload FAILED: Unexpected error: %s', str(e))
    return False

def deleteFromS3(S3Key, config):
  """
  Delete object from S3

  Args:
    S3Key: S3 object key (path in bucket)
    config: App config with AWS credentials and bucket name

  Returns:
    True on success, False on failure
  """
  bucket_name = config['S3_BUCKET_NAME']
  logger.info('Deleting from S3: %s', S3Key)

  try:
    s3 = get_s3_client(config)

    # Remove leading slash if present (boto3 doesn't want it)
    key = S3Key.lstrip('/')

    s3.delete_object(Bucket=bucket_name, Key=key)
    logger.info('S3 Delete SUCCESS: %s', S3Key)
    return True

  except ClientError as e:
    logger.error('S3 Delete FAILED: %s - %s', S3Key, str(e))
    return False
  except Exception as e:
    logger.error('S3 Delete FAILED: Unexpected error: %s', str(e))
    return False

def getPrivateURL(config, S3Key, expiry=3600):
  """
  Generate a signed URL for private S3 objects

  Args:
    config: App config with AWS credentials and bucket name
    S3Key: S3 object key (path in bucket)
    expiry: URL expiry in seconds (default: 3600 = 1 hour)

  Returns:
    Signed URL string or None on error
  """
  bucket_name = config['S3_BUCKET_NAME']

  try:
    s3 = get_s3_client(config)

    # Generate presigned URL (boto3 style)
    url = s3.generate_presigned_url(
      'get_object',
      Params={
        'Bucket': bucket_name,
        'Key': S3Key
      },
      ExpiresIn=expiry
    )

    return url

  except ClientError as e:
    logger.error('S3 Signed URL generation failed: %s - %s', S3Key, str(e))
    return None
  except Exception as e:
    logger.error('S3 Signed URL generation failed: Unexpected error: %s', str(e))
    return None
