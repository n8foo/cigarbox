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
from werkzeug.utils import secure_filename

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

def processPhoto(filename,localSha1='0',clientfilename=None):
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
  saveImportMeta(photo_id,filename,importSource=os.uname()[1],S3=S3success,sha1=sha1,clientfilename=clientfilename)
  return(photo_id)

@app.route('/api/upload', methods=['POST'])
def apiupload():
  # Get the name of the uploaded files
  uploaded_files = request.files.getlist('files')
  if 'sha1' in request.form:
    localSha1 = request.form['sha1']
  else:
    localSha1 = '0'
  response=dict()
  photo_ids=set()

  # check for tags and populate array and response
  if 'tags' in request.form:
    tags = request.form['tags'].split(',')
    response['tags'] = tags
  else:
    tags = None

  clientfilename = request.form['clientfilename']

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
      try:
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
      except Exception as e:
        logger.info('could not save file %s' % os.path.join(app.config['UPLOAD_FOLDER'], filename))
        raise e
      else:
        logger.info('uploaded file saved: %s' % os.path.join(app.config['UPLOAD_FOLDER'], filename))
      # process each file
      photo_id=processPhoto(os.path.join(app.config['UPLOAD_FOLDER'], filename),localSha1,clientfilename=clientfilename)
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
  return jsonify(response)


@app.route('/api/photos/addtags', methods=['POST'])
def photosAddTags():
  data = request.get_json()
  photo_id = data['photo_id']
  logger.info('tags: {}'.format(data['tags']))
  tags=list
  response=dict()

  # if tags is somehow not a list, split on a comma and make it one
  if isinstance(data['tags'],list):
    tags = data['tags']
    logger.info('list tags: {}'.format(tags))
  else:
    tags = data['tags'].split(',')
    logger.info('split tags: {}'.format(tags))

  for tag in tags:
    try:
      photosAddTag(photo_id,tag)
    except Exception as e:
      logger.info('photo_id {} error on tag {}'.format(photo_id,tag))
      raise
    else:
      logger.info('photo_id {} gets tag {}'.format(photo_id,tag))
  response['photo_id'] = photo_id
  response['tags'] =  tags
  return jsonify(response)


@app.route('/api/photos/removetags', methods=['POST'])
def photosRemoveTags():
  data = request.get_json()
  photo_id = data['photo_id']
  logger.info('tags: {}'.format(data['tags']))
  tags=list
  response=dict()

  # if tags is somehow not a list, split on a comma and make it one
  if isinstance(data['tags'],list):
    tags = data['tags']
    logger.info('list tags: {}'.format(tags))
  else:
    tags = data['tags'].split(',')
    logger.info('split tags: {}'.format(tags))

  for tag in tags:
    try:
      photosRemoveTag(photo_id,tag)
    except Exception as e:
      logger.info('photo_id {} error on tag {}'.format(photo_id,tag))
      raise
    else:
      logger.info('photo_id {} disassociated from tag {}'.format(photo_id,tag))
  response['photo_id'] = photo_id
  response['tags'] =  tags
  return jsonify(response)



@app.route('/postjson', methods = ['POST'])
def postJsonHandler():
    content = request.get_json()
    print (content)
    return 'JSON posted'



@app.route('/api/sha1/<string:sha1>')
def show_photo_from_sha1(sha1):
  """a single photo"""
  response=dict()

  try:
    photo = Photo.select().where(Photo.sha1 == sha1).get()
  except Exception as e:
    response['exists'] = False
    response['status'] = "Not Found"
  else:
    (sha1Path,filename) = util.getSha1Path(photo.sha1)
    photo.uri = sha1Path + '/' + filename
    photo_id = str(photo.id)
    response['photo_id'] = photo_id
    response['exists'] = True
    response['path'] = photo.uri
    response['status'] = "Found"
  finally:
    return jsonify(response)
    logger.info(response)

app.config['DEBUG'] = True

if __name__ == '__main__':
  app.run(port=9601)