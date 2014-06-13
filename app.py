#!/usr/bin/env python
# -*- coding:utf-8 -*-

from flask import Flask
from config import *

# create the app
app = Flask(__name__)

# Load default config and override config from config file
app.config.from_object('config')