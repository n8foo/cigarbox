INSERT INTO photo
      (id,datetaken,filetype,privacy,sha1,ts) 
SELECT id,dateTaken,fileType,privacy,sha1,ts 
       FROM photos;

INSERT INTO tag
      (id,name,ts) 
SELECT id,tag, ts 
       FROM tags;

INSERT INTO photoset
      (id,description,title,ts) 
SELECT id,description,title,ts 
       FROM photosets;

INSERT INTO phototag
      (id,photo_id,tag_id,ts) 
SELECT id,photo_id,tag_id,ts 
       FROM tags_photos;

INSERT INTO importmeta
      (id,sha1,photo,importpath,importsource,filedate,s3,ts) 
SELECT 
  import_meta.id, photo.sha1 ,import_meta.photo_id,import_meta.importPath,
  import_meta.importSource,import_meta.fileDate,import_meta.S3,import_meta.ts 
       FROM import_meta,photo
       WHERE import_meta.photo_id = photo.id;

INSERT INTO user
      (id,email,password,active,confirmed_at,ts)
SELECT id,email,password,active,confirmed_at,ts
       FROM user_old;

INSERT INTO photophotoset
      (id,photo_id,photoset_id,ts)
SELECT id,photo_id,photoset_id,ts
       FROM photosets_photos;

DROP TABLE photos;
DROP TABLE tags;
DROP TABLE photosets;
DROP TABLE tags_photos;
DROP TABLE import_meta;
DROP TABLE photosets_photos;
DROP TABLE user_old;
DROP TABLE galleries_photosets;
DROP TABLE comments;
DROP TABLE galleries;
