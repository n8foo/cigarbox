# Statement for enabling the development environment
DEBUG = True

# Define the application directory
import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))  

# Photo archive directory
# local
LOCALARCHIVEPATH='static/cigarbox'
REMOTEARCHIVEPATH='static/cigarbox'

# For directory tagging, ignore these directories/tags
IGNORETAGS = ['Users','Pictures']



# AWS Credentials
AWS_ACCESS_KEY_ID = ''
AWS_SECRET_ACCESS_KEY = ''
S3_BUCKET_NAME=''
# Should we store your originals publicly? Probably not
AWSPOLICY = 'private'

# Define the database - we are working with
# SQLite for this example

DATABASE='photos.db'
USERNAME='admin'
PASSWORD='changeme2014'

# Secrete Key
SECRET_KEY=''

PRIVACYFLAGS = {'public':0, 'friends':1, 'family':2, 'private':8, 'disabled':9}

PER_PAGE=100

SITEURL = 'http://127.0.0.1:5000'
# Application threads. A common general assumption is
# using 2 per available processor cores - to handle
# incoming requests using one and performing background
# operations using the other.
THREADS_PER_PAGE = 2

# Enable protection agains *Cross-site Request Forgery (CSRF)*
CSRF_ENABLED     = True

# Use a secure, unique and absolutely secret key for
# signing the data. 
CSRF_SESSION_KEY = 'secret'

# Secret key for signing cookies
SECRET_KEY = 'secret'

