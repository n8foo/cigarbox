# config

# code functions

* import image
  - read exif
  - read dir structure
    + assign 'set' based on -1 dir
    + assign 'gallery' based on -2 dir
    + all other dirs are tags
  - rename original file
  - add new info to db

* display
  - index
    + by date (years?)
    + most recent
    + tags
    + sets
    + galleries
  - by year
    + straight list
    + set list
  - recent
    + 100 most recent?
  - tag
    + alpha
    + recent
    + by date
  - set
    + alpha
    + recent
    + by date
    + grouped by year
  - gallery
    + alpha
    + most recent
    + by date
    + grouped by year


# database layout
* pictures
  - id (autoenc)
  - sha1
  - date taken
  - orig name
  - tag_id
* tags
  - id
  - name
* sets
  - id
  - name
* gallery
  - id
  - name