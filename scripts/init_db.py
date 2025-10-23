#! /usr/bin/env python

# -*- coding: utf-8 -*-

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import *
from db import *
import util, aws

logger = util.setup_custom_logger('cigarbox')

from flask import Flask, g
app = Flask(__name__)

# Load default config and override config from config file
app.config.from_object('config')

localArchivePath=app.config['LOCALARCHIVEPATH']

@app.teardown_appcontext
def teardown_db(exception):
  """Closes the database again at the end of the request."""
  db = getattr(g, '_database', None)
  if db is not None:
      db.close()

def create_tables(models):
  for model in models:
    try:
      model.drop_table(fail_silently=True)
    except Exception as e:
      raise e
    else:
      logger.info('Creating table for model %s' % model)
    finally:
      model.create_table(fail_silently=False)

def main():
  """Main program"""
  logger.info('Creating Tables')
  create_tables([Photo,Comment,Gallery,Photoset,Tag,PhotoPhotoset,PhotosetGallery,PhotoTag,ImportMeta,Role,User,UserRoles])



# MAIN

if __name__ == "__main__":
  # set an app context so Flask g works #hack
  ctx = app.test_request_context()
  ctx.push()

  main()
  ctx.push()

