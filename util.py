#! /usr/bin/env python

"""utility methods"""

import re, os.path, hashlib, logging
from PIL import Image,ExifTags
from PIL.ExifTags import TAGS,GPSTAGS
# our own libs
import aws

# set up logging
logger = logging.getLogger('cigarbox')


def setup_custom_logger(name):
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger

def genThumbnail(filename,thumbnailType,config,regen=False):
  """generate a single thumbnail from a filename"""
  # define the sizes of the various thumbnails
  thumbnailTypeDefinitions={
    's': (75,75), #should be square eventually
    'q': (150,150), #should be square eventually
    't': (100,100),
    'm': (240,240),
    'n': (320,230),
    'k': (500,500),
    'c': (800,800),
    'b': (1024,1024)}
  size = thumbnailTypeDefinitions[thumbnailType]
  thumbFilename = filename.split('.')[0] + '_' + thumbnailType + '.' + filename.split('.')[1]
  if os.path.isfile(config['LOCALARCHIVEPATH']+'/'+thumbFilename) and regen == False:
    return(thumbFilename)
  else:
    try:
      logger.info('Generating thumbnail: %s' %(config['LOCALARCHIVEPATH']+'/'+thumbFilename))
      img = Image.open(config['LOCALARCHIVEPATH']+'/'+filename)
      icc_profile = img.info.get('icc_profile')
      img.thumbnail(size,Image.ANTIALIAS)
      img.save(config['LOCALARCHIVEPATH']+'/'+thumbFilename, 'JPEG', icc_profile=icc_profile, quality=95)
      return(thumbFilename)
    except IOError as e:
      raise e

def genThumbnails(sha1,fileType,config,regen=False):
  """takes sha1, filetype, config and runs thumbnail generation for all sizes"""
  (sha1Path,filename) = getSha1Path(sha1)
  relativeFilename = '%s/%s.%s' % (sha1Path,filename,fileType)

  thumbnailTypes = ['t','m','n','c','b']
  thumbnailFilenames = []
  for thumbnailType in thumbnailTypes:
    thumbFilename = genThumbnail(relativeFilename,thumbnailType,config,regen=regen)
    thumbnailFilenames.append(thumbFilename)
  return thumbnailFilenames


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
  """returns a list consisting of (sha1Path,filename)"""
  dir1=sha1[:2]
  dir2=sha1[2:4]
  dir3=sha1[4:6]
  filename=sha1[6:40]
  return(dir1+'/'+dir2+'/'+dir3,filename)

def hashfile(filename):
  """returns a sha1 hash of a local file"""
  BLOCKSIZE = 65536
  sha1 = hashlib.sha1()
  with open(filename, 'rb') as afile:
    buf = afile.read(BLOCKSIZE)
    while len(buf) > 0:
        sha1.update(buf)
        buf = afile.read(BLOCKSIZE)
  return(sha1.hexdigest())

def getArchiveURI(sha1,archivePath,fileType='jpg'):
  """returns absolute path to archive file"""
  (sha1Path,filename)=getSha1Path(sha1)
  return(archivePath+'/'+sha1Path+'/'+filename+'.'+fileType)

def getExifTags(filename):
  img = Image.open(filename)
  try:
    raw_exif = img._getexif()
    exif = {ExifTags.TAGS.get(tag, tag): value
      for (tag, value) in raw_exif.iteritems()}
  except Exception, e:
    return None
  # Process GPS Info, if it's there
  if 'GPSInfo' in exif.iteritems():
    # Calculate Lat/Lon from GPS raw
    Nsec = exif['GPSInfo'][2][2][0] / float(exif['GPSInfo'][2][2][1])
    Nmin = exif['GPSInfo'][2][1][0] / float(exif['GPSInfo'][2][1][1])
    Ndeg = exif['GPSInfo'][2][0][0] / float(exif['GPSInfo'][2][0][1])
    Wsec = exif['GPSInfo'][4][2][0] / float(exif['GPSInfo'][4][2][1])
    Wmin = exif['GPSInfo'][4][1][0] / float(exif['GPSInfo'][4][1][1])
    Wdeg = exif['GPSInfo'][4][0][0] / float(exif['GPSInfo'][4][0][1])
    if exif['GPSInfo'][3] == 'N':
      Nmult = 1
    else:
      Nmult = -1
    if exif['GPSInfo'][3] == 'E':
      Wmult = 1
    else:
      Wmult = -1
    Latitude = Nmult * (Ndeg + (Nmin + Nsec/60.0)/60.0)
    Longitude = Wmult * (Wdeg + (Wmin + Wsec/60.0)/60.0)
    # Add 2 new decimal Lat/Lon entries to the dict for easy access
    exif['GPSLat'] = Latitude
    exif['GPSLon'] = Longitude
    # Reverse the GPSInfo key/values for easy access by Human Name
    decoded_gps_exif = {ExifTags.GPSTAGS.get(tag,tag): value
      for (tag, value) in exif['GPSInfo'].iteritems()}
    exif['GPSInfo'] = decoded_gps_exif
  return exif


