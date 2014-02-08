#! /usr/bin/env python

"""utility methods"""

import re, exifread

def normalizeString(string):
  string = string.lower()
  string = re.sub(r'[\W\s]','',string)
  return string

def getSha1Path(sha1):
  dir1=sha1[:2]
  dir2=sha1[2:4]
  dir3=sha1[4:6]
  return(dir1+'/'+dir2+'/'+dir3)

def getArchiveURI(sha1,archivePath,fileType='jpg'):
  sha1Path=getSha1Path(sha1)
  return(archivePath+'/'+sha1Path+'/'+sha1+'.'+fileType)

def getExifTags(fileObj,tag=None):
  exifTags = exifread.process_file(fileObj,details=False)
  return exifTags