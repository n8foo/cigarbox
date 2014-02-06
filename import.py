#! /usr/bin/env python

import argparse

parser = argparse.ArgumentParser(description='import photos into photos system.')
parser.add_argument('--files', metavar='N', type=str, nargs='+',
                   help='files to import', required=True)
parser.add_argument('--set', help='assign a set to an import set')
parser.add_argument('--gallery', help='assign a gallery to an import')
parser.add_argument('--tags', help='assign tag(s) to an import')
parser.add_argument('--basedir', help='base directory for the archive', default='photos')
args = parser.parse_args()


ignoreTags = ['Users','nathan','Pictures','www_pics']

import cigarbox, exifread, os, sqlite3, shutil, time,logging,hashlib, re

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

def hashfile(file):
  BLOCKSIZE = 65536
  sha1 = hashlib.sha1()
  with open(file, 'rb') as afile:
    buf = afile.read(BLOCKSIZE)
    while len(buf) > 0:
        sha1.update(buf)
        buf = afile.read(BLOCKSIZE)
  return(sha1.hexdigest())

def normalizeString(string):
  string = string.lower()
  string = re.sub(r'[\W\s]','',string)
  return string

def photosetsAddPhoto(title,photo_id,description=None):
  logging.info('adding photo_id %s to set: %s', photo_id, title)

def addPhoto(sha1,fileType,origFileName,dateTaken):
  logging.info('Adding to DB: %s %s %s %s', sha1,fileType,origFileName,dateTaken)
  c.execute ('SELECT id FROM photos where sha1 = ?',(sha1,))
  photo_id = c.fetchone()
  if photo_id != None:
    return photo_id[0]
  else: 
    c.execute('INSERT INTO photos VALUES(NULL, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)', (sha1, fileType, origFileName, dateTaken,))
    return c.lastrowid

def photosAddTag(photo_id,tag):
  tag = normalizeString(tag)
  logging.info('tagging photo id %s tag: %s', photo_id, tag)
  c.execute ('SELECT id FROM tags WHERE tag=?',(tag,))
  tag_id = c.fetchone()
  if tag_id == None:
    try: 
      c.execute('INSERT INTO tags VALUES(NULL, ?, CURRENT_TIMESTAMP)',(tag,))
      tag_id = c.lastrowid
    except Exception as e:
      # Roll back any change if something goes wrong
      conn.rollback()
      raise e
  else:
    tag_id = tag_id[0]
  # ok now we have the tag_id and photo_id, let's do this
  c.execute ('SELECT id FROM tags_photos WHERE tag_id = ? and photo_id = ?',(tag_id,photo_id))
  tags_photos_id = c.fetchone()
  if tags_photos_id == None:
    c.execute('INSERT INTO tags_photos VALUES(NULL, ?, ?, CURRENT_TIMESTAMP)',(tag_id, photo_id))
    return c.lastrowid
  else:
    tags_photos_id = tags_photos_id[0]
    return tags_photos_id

def getfileType(origFileName):
  fileType = origFileName.split('.')[-1].lower()
  logging.info('File type: %s',fileType)
  return fileType

def getArchivePath(sha1):
  dir1=sha1[:2]
  dir2=sha1[2:4]
  dir3=sha1[4:6]
  return(dir1+'/'+dir2+'/'+dir3)

def archivePhoto(file,sha1,fileType,basedir='photos'):
  archivePath=getArchivePath(sha1)
  logging.info('Copying %s -> %s/%s/%s.%s',file,basedir,archivePath,sha1,fileType)
  if not os.path.isdir(basedir+'/'+archivePath):
    os.makedirs(basedir+'/'+archivePath)
  try:
      shutil.copy2(file,basedir+'/'+archivePath+'/'+sha1+'.'+fileType)
  except Exception, e:
    raise
  return(basedir+'/'+archivePath+'/'+sha1+'.'+fileType)

def importFile(file):
  logging.info('Importing file %s', file)
  f = open(file, 'rb')
  tags = exifread.process_file(f,stop_tag='Image DateTime')
  if tags:
    if 'Image DateTime' in tags:
      dateTaken = str(tags['Image DateTime'])
    else:
      dateTaken = time.ctime(os.path.getmtime(file))
  else:
    dateTaken = time.ctime(os.path.getmtime(file))

  origFileName = os.path.basename(file)
  fileType = getfileType(origFileName)
  sha1=hashfile(file)
  archivePhoto(file,sha1,fileType,args.basedir)

  # insert pic into db
  photo_id = addPhoto(sha1,fileType,origFileName,dateTaken)


  # tag based on directory structure
  origDirPaths = os.path.dirname(file).split('/')
  for dir in origDirPaths:
    tag = str(dir)
    if tag != '':
      if tag not in ignoreTags:
        photosAddTag(photo_id,tag)



# my code here

conn = sqlite3.connect('photos.db')
c = conn.cursor()

for file in args.files:
  importFile(file)

conn.commit()
conn.close()

def main():
  # main
  print 'done'

if __name__ == "__main__":
    main()

