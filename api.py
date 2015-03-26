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
from resources.upload import Upload
from werkzeug import secure_filename

# cigarbox
from app import *
import util, aws
import os
from web import allowed_file
from process import *

app = Flask(__name__)

app.config.from_object('config')
localArchivePath=app.config['LOCALARCHIVEPATH']

logger = util.setup_custom_logger('cigarbox')

# define a few variables for the API
uploadToS3=True

def processPhoto(filename):
  # log what we're doing
  logger.info('Processing file %s', filename)


  # set some variables
  dateTaken=getDateTaken(filename)
  fileType = getfileType(os.path.basename(filename))
  sha1=util.hashfile(filename)

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
  saveImportMeta(photo_id,filename,importSource=os.uname()[1],S3=S3success)
  return(photo_id)

@app.route('/api/upload', methods=['POST'])
def upload():
  # Get the name of the uploaded files
  uploaded_files = request.files.getlist('file[]')
  photo_ids=set()
  for file in uploaded_files:
    # Check if the file is one of the allowed types/extensions
    if file and allowed_file(file.filename):
      # Make the filename safe, remove unsupported chars
      filename = secure_filename(file.filename)
      # Move the file form the temporal folder to the upload
      # folder we setup
      file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
      # process each file
      photo_id=processPhoto(os.path.join(app.config['UPLOAD_FOLDER'], filename))
      photo_ids.add(photo_id)
  # turn back into a list since set is not jsonifyable 
  photo_ids=list(photo_ids)
  return jsonify({'photo_ids': photo_ids})

app.config['DEBUG'] = True

if __name__ == '__main__':
  app.run(port=5001)