#! /usr/bin/env python

"""utility methods"""

import re, exifread, os.path
from PIL import Image

def genThumbnail(filename,abbr,regen=False):
  '''generate a single thumbnail'''
  # define the sizes of the various thumbnails
  thumbnailDefinitions={
    's': (75,75), #should be square eventually
    'q': (150,150), #should be square eventually
    't': (100,100),
    'm': (240,240),
    'n': (320,230),
    'k': (500,500),
    'c': (800,800),
    'b': (1024,1024)}
  size = thumbnailDefinitions[abbr]
  thumbFileName = filename.split('.')[0] + '_' + abbr + '.jpg'
  if os.path.isfile(thumbFileName) and regen == False:
    return(thumbFileName)
  else:
    try:
      im = Image.open(filename)
      icc_profile = im.info.get('icc_profile')
      im.thumbnail(size,Image.ANTIALIAS)
      im.save(thumbFileName, 'JPEG', icc_profile=icc_profile, quality=95)
      return(thumbFileName)
    except IOError as e:
      raise e

def genThumbnails(filename,regen):
  genThumbnail(filename,abbr='t',regen=regen)
  genThumbnail(filename,abbr='m',regen=regen)
  genThumbnail(filename,abbr='n',regen=regen)
  genThumbnail(filename,abbr='c',regen=regen)
  genThumbnail(filename,abbr='b',regen=regen)


# base58 functions for short URL's

alphabet = '123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ'
base = len(alphabet)

def b58encode(div, s=''):
  if div >= base:
    div, mod = divmod(div, base)
    return b58encode(div, alphabet[mod] + s)
  return alphabet[div] + s

def b58decode(s):
  return sum(alphabet.index(c) * pow(base, i) for i, c in enumerate(reversed(s)))


def normalizeString(string):
  string = string.lower()
  string = re.sub(r'[\W\s]','',string)
  return string

def getSha1Path(sha1):
  """returns sha1 dir structure"""
  dir1=sha1[:2]
  dir2=sha1[2:4]
  dir3=sha1[4:6]
  return(dir1+'/'+dir2+'/'+dir3)

def getArchiveURI(sha1,archivePath,fileType='jpg'):
  """returns absolute path to archive file"""
  sha1Path=getSha1Path(sha1)
  return(archivePath+'/'+sha1Path+'/'+sha1+'.'+fileType)

def getExifTags(fileObj,tag=None):
  exifTags = exifread.process_file(fileObj,details=False)
  return exifTags