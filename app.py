#!/usr/bin/env python
# -*- coding:utf-8 -*-

import logging
import sys
from flask import Flask
from config import *

# create the app
app = Flask(__name__)

# Load default config and override config from config file
app.config.from_object('config')

# Configure logging for better error visibility
if not app.debug:
    # Set up logging to stderr (captured by Docker/gunicorn)
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.ERROR)
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.ERROR)

# Log all unhandled exceptions
@app.errorhandler(Exception)
def handle_exception(e):
    # Pass through HTTP errors
    if hasattr(e, 'code'):
        return e
    # Log the error
    app.logger.error(f'Unhandled exception: {str(e)}', exc_info=True)
    return "Internal Server Error", 500