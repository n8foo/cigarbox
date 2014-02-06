#! /usr/bin/env python

import argparse

parser = argparse.ArgumentParser(description='import photos into photos system.')
parser.add_argument('--files', metavar='N', type=str, nargs='+',
                   help='files to import', required=True)
parser.add_argument('--set', help='assign a set to an import set')
parser.add_argument('--gallery', help='assign a gallery to an import')
parser.add_argument('--tags', help='assign tag(s) to an import')
args = parser.parse_args()


ignoreTags = ['Users','nathan','Pictures','www_pics']

import hashlib, exifread, os, sqlite3, logging, shutil, time, re

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

def addPhoto(sha1,fileType,origFileName,dateTaken):
  logging.info('Adding to DB: %s %s %s %s', sha1,fileType,origFileName,dateTaken)
  c.execute ('SELECT id FROM photos where sha1 = ?',(sha1,))
  photo_id = c.fetchone()
  if photo_id != None:
    return photo_id[0]
  else: 
    c.execute('INSERT INTO photos VALUES(NULL, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)', (sha1, fileType, origFileName, dateTaken,))
    return c.lastrowid

def tagPhoto(tagName,photo_id):
  logging.info('tagging photo id %s tag: %s', photo_id, tagName)
  tagName = tagName.lower()
  tagName = re.sub(r'[^\w\s]','',tagName)
  c.execute ('SELECT id FROM tags WHERE name=?',(tagName,))
  id_tag = c.fetchone()
  if id_tag == None:
    try: 
      c.execute('INSERT INTO tags VALUES(NULL, ?, CURRENT_TIMESTAMP)',(tagName,))
      id_tag = c.lastrowid
    except Exception as e:
      # Roll back any change if something goes wrong
      conn.rollback()
      raise e
  else:
    id_tag = id_tag[0]
  # ok now we have the id_tag and photo_id, let's do this
  c.execute ('SELECT id FROM tags_photos WHERE id_tag = ? and photo_id = ?',(id_tag,photo_id))
  id_tags_photos = c.fetchone()
  if id_tags_photos == None:
    c.execute('INSERT INTO tags_photos VALUES(NULL, ?, ?, CURRENT_TIMESTAMP)',(id_tag, photo_id))
    return c.lastrowid
  else:
    id_tags_photos = id_tags_photos[0]
    return id_tags_photos

def getfileType(origFileName):
  fileType = origFileName.split('.')[-1].lower()
  logging.info('File type: %s',fileType)
  return fileType

def getNewFilePath(sha1,fileType):
  newDirPath=getNewDirPath(sha1)
  return(newDirPath+'/'+sha1+'.'+fileType)

def getNewDirPath(sha1):
  dir1=sha1[:2]
  dir2=sha1[2:4]
  dir3=sha1[4:6]
  return(dir1+'/'+dir2+'/'+dir3)

def addToNewFilePath(file,sha1,fileType):
  newDirPath=getNewDirPath(sha1)
  logging.info('Copying %s -> %s/%s.%s',file,newDirPath,sha1,fileType)
  if not os.path.isdir('photos/'+newDirPath):
    os.makedirs('photos/'+newDirPath)
  try:
      shutil.copy2(file,'photos/'+newDirPath+'/'+sha1+'.'+fileType)
  except Exception, e:
    raise
  return(newDirPath+'/'+sha1+'.'+fileType)

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
  addToNewFilePath(file,sha1,fileType)

  # insert pic into db
  photo_id = addPhoto(sha1,fileType,origFileName,dateTaken)


  # tag based on directory structure
  origDirPaths = os.path.dirname(file).split('/')
  for dir in origDirPaths:
    tagName = str(dir)
    if tagName != '':
      if tagName in ignoreTags:
        print 'skipping tag '+tagName
      else:
        tagPhoto(tagName,photo_id)



# my code here

conn = sqlite3.connect('photos.db')
c = conn.cursor()

for file in args.files:
  importFile(file)

conn.commit()
conn.close()

def main():
  # main
  print 'yes'

if __name__ == "__main__":
    main()

