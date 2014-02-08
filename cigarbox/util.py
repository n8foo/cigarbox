#! /usr/bin/env python

"""utility methods"""

import re

def normalizeString(string):
  string = string.lower()
  string = re.sub(r'[\W\s]','',string)
  return string

def getArchivePath(sha1):
  dir1=sha1[:2]
  dir2=sha1[2:4]
  dir3=sha1[4:6]
  return(dir1+'/'+dir2+'/'+dir3)

def getArchiveURI(sha1,basedir,fileType='jpg'):
  archivePath=getArchivePath(sha1)
  return(basedir+'/'+archivePath+'/'+sha1+'.'+fileType)