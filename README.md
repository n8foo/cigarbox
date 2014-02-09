CigarBox
========
A smokin' fast personal photostream

# design points
* lightweight enought to run well on an $8/mo EC2 instance
* RESTful API
* similar nomenclature & photo graph to flickr
  - photos
  - photosets
  - galleries
  - tags
* #simplify

# install
### OSX
1. Install homebrew
2. brew install libtiff libjpeg webp littlecms
3. pip install Pillow ExifRead Flask

### Ubuntu 12.04LTS
1. sudo apt-get install libtiff4-dev libjpeg8-dev zlib1g-dev libfreetype6-dev liblcms2-dev libwebp-dev tcl8.5-dev tk8.5-dev
2. pip install Pillow ExifRead Flask