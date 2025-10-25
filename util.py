#! /usr/bin/env python

"""utility methods"""

import re, os.path, hashlib, logging
from PIL import Image,ExifTags
from PIL.ExifTags import TAGS,GPSTAGS
# our own libs
import aws

# set up logging
logger = logging.getLogger('cigarbox')


def setup_custom_logger(name, service_name='app'):
    """Setup logger that writes to both console and shared file

    Args:
        name: Logger name (usually 'cigarbox')
        service_name: Service identifier ('web' or 'api') to distinguish containers
    """
    # Format: timestamp [SERVICE] LEVEL - module - message
    formatter = logging.Formatter(
        fmt=f'%(asctime)s [{service_name.upper()}] %(levelname)s - %(module)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    # Console handler (for docker logs command)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (shared log file - volume mounted)
    try:
        os.makedirs('/app/logs', exist_ok=True)
        file_handler = logging.FileHandler('/app/logs/cigarbox.log')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f'Could not setup file logging: {e}')

    return logger

def genThumbnail(filename,thumbnailType,config,regen=False):
  """generate a single thumbnail from a filename - always outputs JPG regardless of source format"""
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
  # Always output thumbnails as .jpg regardless of input format
  thumbFilename = filename.split('.')[0] + '_' + thumbnailType + '.jpg'
  thumbFullPath = config['LOCALARCHIVEPATH']+'/'+thumbFilename
  sourceFullPath = config['LOCALARCHIVEPATH']+'/'+filename

  if os.path.isfile(thumbFullPath) and regen == False:
    logger.info('Thumbnail EXISTS (skipping): %s', thumbFilename)
    return(thumbFilename)
  else:
    try:
      logger.info('Thumbnail Generation START: type=%s size=%s source=%s target=%s',
                  thumbnailType, size, filename, thumbFilename)

      # Check if source exists
      if not os.path.exists(sourceFullPath):
        logger.error('Thumbnail Generation FAILED: Source file does not exist: %s', sourceFullPath)
        raise IOError('Source file does not exist: %s' % sourceFullPath)

      img = Image.open(sourceFullPath)
      original_size = img.size
      original_mode = img.mode
      logger.info('Thumbnail Generation: Opened source image size=%s mode=%s', original_size, original_mode)

      # Convert to RGB if necessary (PNG with transparency, palette mode, etc.)
      if img.mode in ('RGBA', 'LA', 'P'):
        logger.info('Thumbnail Generation: Converting from %s to RGB for JPEG output', img.mode)
        # Create white background for images with transparency
        if img.mode == 'P':
          img = img.convert('RGBA')
        if img.mode in ('RGBA', 'LA'):
          background = Image.new('RGB', img.size, (255, 255, 255))
          background.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
          img = background
        else:
          img = img.convert('RGB')
      elif img.mode != 'RGB':
        logger.info('Thumbnail Generation: Converting from %s to RGB for JPEG output', img.mode)
        img = img.convert('RGB')

      icc_profile = img.info.get('icc_profile')
      img.thumbnail(size,Image.Resampling.LANCZOS)
      final_size = img.size
      logger.info('Thumbnail Generation: Resized to %s', final_size)

      img.save(thumbFullPath, 'JPEG', icc_profile=icc_profile, quality=95)
      thumb_file_size = os.path.getsize(thumbFullPath)
      logger.info('Thumbnail Generation SUCCESS: %s created (%d bytes)', thumbFilename, thumb_file_size)
      return(thumbFilename)
    except IOError as e:
      logger.error('Thumbnail Generation FAILED: IOError for %s: %s', thumbFilename, str(e))
      raise e
    except Exception as e:
      logger.error('Thumbnail Generation FAILED: Unexpected error for %s: %s', thumbFilename, str(e))
      raise e

def genThumbnails(sha1,fileType,config,regen=False):
  """takes sha1, filetype, config and runs thumbnail generation for all sizes"""
  (sha1Path,filename) = getSha1Path(sha1)
  relativeFilename = '%s/%s.%s' % (sha1Path,filename,fileType)

  logger.info('Thumbnail Batch START: sha1=%s filetype=%s source=%s', sha1, fileType, relativeFilename)

  thumbnailTypes = ['t','m','n','c','b']
  thumbnailFilenames = []
  success_count = 0
  fail_count = 0

  for thumbnailType in thumbnailTypes:
    try:
      thumbFilename = genThumbnail(relativeFilename,thumbnailType,config,regen=regen)
      thumbnailFilenames.append(thumbFilename)
      success_count += 1
    except Exception as e:
      logger.error('Thumbnail Batch: Failed to generate type %s: %s', thumbnailType, str(e))
      fail_count += 1

  logger.info('Thumbnail Batch COMPLETE: sha1=%s success=%d failed=%d total=%d',
              sha1, success_count, fail_count, len(thumbnailTypes))

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
      for (tag, value) in raw_exif.items()}
  except Exception as e:
    return None
  # Process GPS Info, if it's there
  if 'GPSInfo' in iter(exif.items()):
    try:
      # Calculate Lat/Lon from GPS raw
      gps_info = exif['GPSInfo']
      # Check if all required GPS fields are present
      if (2 in gps_info and 3 in gps_info and 4 in gps_info and
          len(gps_info[2]) >= 3 and len(gps_info[4]) >= 3):
        Nsec = gps_info[2][2][0] / float(gps_info[2][2][1])
        Nmin = gps_info[2][1][0] / float(gps_info[2][1][1])
        Ndeg = gps_info[2][0][0] / float(gps_info[2][0][1])
        Wsec = gps_info[4][2][0] / float(gps_info[4][2][1])
        Wmin = gps_info[4][1][0] / float(gps_info[4][1][1])
        Wdeg = gps_info[4][0][0] / float(gps_info[4][0][1])
        if gps_info[3] == 'N':
          Nmult = 1
        else:
          Nmult = -1
        if gps_info[1] == 'E':
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
        for (tag, value) in gps_info.items()}
      exif['GPSInfo'] = decoded_gps_exif
    except (KeyError, IndexError, ZeroDivisionError, TypeError) as e:
      logger.warning('Error processing GPS info: {}'.format(e))
      # Keep the raw GPS info even if we can't process it
      pass
  return exif


