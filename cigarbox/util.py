#! /usr/bin/env python

"""utility methods"""

import re, exifread

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