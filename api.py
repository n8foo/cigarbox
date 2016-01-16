#! /usr/bin/env python

# -*- coding: utf-8 -*-
"""
  CigarBox
  ~~~~~~

  A smokin' fast personal photostream

  :copyright: (c) 2015 by Nathan Hubbard @n8foo.
  :license: Apache, see LICENSE for more details.
"""


from flask import Flask, request, jsonify
#from resources.upload import Upload
from werkzeug import secure_filename

# cigarbox
from app import *
import util, aws
from web import allowed_file
from process import *

#standard libs

import os

app = Flask(__name__)

app.config.from_object('config')
localArchivePath=app.config['LOCALARCHIVEPATH']

logger = util.setup_custom_logger('cigarbox')

# define a few variables for the API
uploadToS3=True

def processPhoto(filename,localSha1='0'):
  # log what we're doing
  logger.info('Processing file %s', filename)

  # set some variables
  dateTaken=getDateTaken(filename)
  fileType = getfileType(os.path.basename(filename))
  sha1=util.hashfile(filename)

  # check sha1 local against sha1 server
  if localSha1 == '0':
    logger.info('no SHA1 sent. oh well.')
  elif localSha1 != sha1:
    logger.error('SHA1 signatures DO NOT MATCH!')
  elif localSha1 == sha1:
    logger.info('SHA1 verified.')
  else:
    logger.info('SHA1 unknown state')

  # insert pic into db
  photo_id = addPhotoToDB(sha1=sha1,fileType=fileType,dateTaken=dateTaken)

  # archive the photo
  archivedPhoto=archivePhoto(filename,sha1,fileType,localArchivePath,uploadToS3,photo_id)

  # generate thumbnails
  thumbFilenames = util.genThumbnails(sha1,fileType,app.config)
  # send thumbnails to S3
  if checkImportStatusS3(photo_id) == False:
    for thumbFilename in thumbFilenames:
      S3success = aws.uploadToS3(localArchivePath+'/'+thumbFilename,thumbFilename,app.config,regen=True,policy='public-read')
  else:
    S3success = False

  # save import meta
  saveImportMeta(photo_id,filename,importSource=os.uname()[1],S3=S3success,sha1=sha1)
  return(photo_id)

@app.route('/api/upload', methods=['POST'])
def apiupload():
  # Get the name of the uploaded files
  uploaded_files = request.files.getlist('files')
  if 'sha1' in request.form:
    localSha1 = request.form['sha1']
  else:
    localSha1 = '0'
  print request.form
  response=dict()
  photo_ids=set()

  # check for tags and populate array and response
  if 'tags' in request.form:
    tags = request.form['tags'].split(',')
    response['tags'] = tags
  else:
    tags = None

  # check for photoset and populate array and response
  if 'photoset' in request.form:
    photoset = request.form['photoset']
    response['photoset'] = photoset
    photoset_id = photosetsCreate(photoset)
  else:
    photoset = None

  for file in uploaded_files:
    # Check if the file is one of the allowed types/extensions
    if file and allowed_file(file.filename):
      # Make the filename safe, remove unsupported chars
      filename = secure_filename(file.filename)
      # Move the file form the temporal folder to the upload
      # folder we setup
      file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
      # process each file
      photo_id=processPhoto(os.path.join(app.config['UPLOAD_FOLDER'], filename),localSha1)
      photo_ids.add(photo_id)

      # add tags for each photo
      if tags:
        for tag in tags:
          photosAddTag(photo_id,tag)

      # add to photoset
      if photoset:
        photosetsAddPhoto(photoset_id,photo_id)



  # turn back into a list since set is not jsonifyable 
  photo_ids=list(photo_ids)
  response['photo_ids'] = photo_ids
  print response
  return jsonify(response)

app.config['DEBUG'] = True

if __name__ == '__main__':
  app.run(port=9001)