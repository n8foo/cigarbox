"""Gunicorn configuration for CigarBox"""
import os
import multiprocessing

# Server socket
bind = "0.0.0.0:9600"  # Default, overridden by command line
backlog = 2048

# Worker processes
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'sync'
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 300  # 5 minutes for long-running operations like EXIF scan
keepalive = 2

# Logging
accesslog = '/app/logs/gunicorn_access.log'
errorlog = '/app/logs/gunicorn_error.log'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'cigarbox'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = '/tmp/cigarbox'

# Development vs Production
reload = os.getenv('FLASK_ENV') == 'development'
reload_engine = 'auto'

def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Starting CigarBox server")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading CigarBox server")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("CigarBox server is ready. Listening on: %s", server.cfg.bind)

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info("Worker received INT or QUIT signal")

def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal."""
    worker.log.info("Worker received SIGABRT signal")
