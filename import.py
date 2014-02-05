#! /usr/bin/env python

import argparse

parser = argparse.ArgumentParser(description='import photos into pictures system.')
parser.add_argument('--files', metavar='N', type=str, nargs='+',
                   help='files to import', required=True)
parser.add_argument('--set', help='assign a set to an import set')
parser.add_argument('--gallery', help='assign a gallery to an import')
parser.add_argument('--tags', help='assign tag(s) to an import')
args = parser.parse_args()


import hashlib, exifread, os, sqlite3, logging, shutil, time

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

def addPicture(sha1,fileType,origFileName,dateTaken):
  logging.info('Adding to DB: %s %s %s %s', sha1,fileType,origFileName,dateTaken)
  c.execute ('SELECT id FROM pictures where sha1 = ?',(sha1,))
  id_picture = c.fetchone()
  if id_picture != None:
    return id_picture[0]
  else: 
    c.execute('INSERT INTO pictures VALUES(NULL, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)', (sha1, fileType, origFileName, dateTaken,))
    return c.lastrowid

def tagPicture(tagName,id_picture):
  logging.info('tagging picture id %s tag: %s', id_picture, tagName)
  tagName = tagName.lower()
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
  # ok now we have the id_tag and id_picture, let's do this
  c.execute ('SELECT id FROM tags_pictures WHERE id_tag = ? and id_picture = ?',(id_tag,id_picture))
  id_tags_pictures = c.fetchone()
  if id_tags_pictures == None:
    c.execute('INSERT INTO tags_pictures VALUES(NULL, ?, ?, CURRENT_TIMESTAMP)',(id_tag, id_picture))
    return c.lastrowid
  else:
    id_tags_pictures = id_tags_pictures[0]
    return id_tags_pictures

def getfileType(origFileName):
  fileType = origFileName.split('.')[-1].lower()
  logging.info('File type: %s',fileType)
  return fileType

def getNewFilePath(sha1,fileType):
  dir1=sha1[:2]
  dir2=sha1[2:4]
  dir3=sha1[4:6]
  logging.info('New Path: %s/%s/%s/%s.%s',dir1,dir2,dir3,sha1,fileType)
  return(dir1+'/'+dir2+'/'+dir3+'/'+sha1+'.'+fileType)

def addToNewFilePath(file,sha1,fileType):
  dir1=sha1[:2]
  dir2=sha1[2:4]
  dir3=sha1[4:6]
  logging.info('Copying %s -> %s/%s/%s/%s.%s',file,dir1,dir2,dir3,sha1,fileType)
  if not os.path.isdir('pictures/'+dir1+'/'+dir2+'/'+dir3):
    os.makedirs('pictures/'+dir1+'/'+dir2+'/'+dir3)
  try:
      shutil.copy2(file,'pictures/'+dir1+'/'+dir2+'/'+dir3+'/'+sha1+'.'+fileType)
  except Exception, e:
    raise
  return(dir1+'/'+dir2+'/'+dir3+'/'+sha1+'.'+fileType)

def importFile(file):
  logging.info('Importing file %s', file)
  f = open(file, 'rb')
  tags = exifread.process_file(f)
  if tags:
    dateTaken = str(tags['Image DateTime'])
  else:
    dateTaken = time.ctime(os.path.getmtime(file))

  origFileName = os.path.basename(file)
  fileType = getfileType(origFileName)
  sha1=hashfile(file)
  newFilePath = getNewFilePath(sha1,fileType)
  addToNewFilePath(file,sha1,fileType)

  # insert pic into db
  id_picture = addPicture(sha1,fileType,origFileName,dateTaken)


  # tag based on directory structure
  origDirPaths = os.path.dirname(file).split('/')
  for dir in origDirPaths:
    tagName = str(dir)
    if tagName != '':
      tagPicture(tagName,id_picture)



# my code here

conn = sqlite3.connect('pictures.db')
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

