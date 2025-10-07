#! /bin/env/python

from fabric.api import *
from contextlib import *

import time
import os

env.use_ssh_config=True

env.roledefs = {
  'cigarbox': ['cigarbox'],
  'docker_remote':['piston'],
}


deployfiles=[
  "api",
  "app",
  "aws",
  "db",
  "process",
  "setup",
  "util",
  "web"
  ]

ts=str(int(time.time()))

@task
@roles('cigarbox')
def pushdb():
  backup()
  with cd('cigarbox'):
    put('photos.db','photos.db')
  restart()

@task
@roles('cigarbox')
def pulldb():
  with cd('cigarbox'):
    get('photos.db','photos.db')

@task
@roles('cigarbox')
def backup():
  local('echo .dump | sqlite3 photos.db |gzip -c > backups/'+ts+'.sql.gz')
  with cd('backups'),lcd('backups'):
    put(ts+'.sql.gz',ts+'.sql.gz')

@task
@roles('cigarbox')
def install():
  run('mkdir cigarbox')
  run('mkvirtualenv -a ~/cigarbox cigarbox')
  put('cigarbox.monit','cigarbox.monit')
  sudo('mv cigarbox.monit /etc/monit/conf.d/cigarbox')
  sudo('chown root.root /etc/monit/conf.d/cigarbox')
  sudo('monit reload')


@task
@roles('docker')
def docker():
  run('mkdir -pv docker/cigarbox')
  with cd('docker/cigarbox'):
    run('mkdir -pv static templates')
    for deployfile in deployfiles:
      put(deployfile+'.py',deployfile+'.py')
    put('Dockerfile','Dockerfile')
    put('templates/*','templates')
    put('photos.db','photos.db')
    put('requirements.txt','requirements.txt')
    put('docker_start.sh','docker_start.sh')
    run('docker build -t cigarbox .')

@task
@roles('cigarbox')
def deploy():
  with cd('cigarbox'):
    for deployfile in deployfiles:
      put(deployfile+'.py',deployfile+'.py')
  put('templates','cigarbox/')
  restart()

@task
@roles('cigarbox')
def restart():
  sudo('monit restart cigarbox')

@task
def restore(file):
  local('rm -f photos.db')
  local('/usr/bin/gunzip -c '+file+' | sqlite3 photos.db')

@task
def server():
  local('mkdir  -pv /tmp/cigarbox')
  local('./web.py')

@task
def apiserver():
  local('mkdir  -pv /tmp/cigarbox')
  local('./api.py')

@task
def cleanup():
  local('find /tmp/cigarbox -type f -delete -print')

@task
def migrate(migration):
  execute(backup)
  local('bash -x maintenance/migrations/%s.sh'% migration)

@task
def test():
  """Run unit tests"""
  local('python run_tests.py')

@task
@roles('docker_remote')
def test_remote():
  """Run unit tests on remote docker server"""
  with cd('~/docker/cigarbox'):
    run('docker-compose exec -T web python run_tests.py')

@task
def test_integration():
  """Run integration tests against running server"""
  urls=['/','/photostream','/tags','/tags/misc','/photosets','/photosets/1068','/photosets/1010/page/2']
  for url in urls:
    local('curl -sS -vL http://127.0.0.1:9600%s -o /dev/null' % url)

@task
@roles('docker_remote')
def docker_logs_remote():
  """Show Docker container logs on remote server"""
  with cd('~/docker/cigarbox'):
    run('docker-compose logs --tail=50')

@task
@roles('docker_remote')
def docker_status_remote():
  """Check Docker container status on remote server"""
  with cd('~/docker/cigarbox'):
    run('docker-compose ps')
    run('docker-compose exec -T web curl -s http://localhost:9600/health || echo "Web health check failed"')
    run('docker-compose exec -T api curl -s http://localhost:9601/api/sha1/test || echo "API health check failed"')

@task
@roles('docker_remote')
def test_integration_remote():
  """Run integration tests against remote Docker deployment"""
  # Set API URL for tests
  with shell_env(CIGARBOX_TEST_API='http://piston:8088/api'):
    local('python test_integration_upload.py -v')

# Docker tasks

@task
@runs_once
def docker_build():
  """Build Docker image"""
  local('docker build -f Dockerfile -t cigarbox:latest .')

@task
@runs_once
def docker_up():
  """Start Docker containers"""
  # Copy .env.example to .env if it doesn't exist
  if not os.path.exists('.env'):
    local('cp .env.example .env')
    print('Created .env from .env.example - please review and customize')
  local('docker-compose up -d')
  local('docker-compose ps')

@task
@runs_once
def docker_down():
  """Stop Docker containers"""
  local('docker-compose down')

@task
@runs_once
def docker_logs(service=''):
  """View Docker logs. Usage: fab docker_logs or fab docker_logs:service=web"""
  if service:
    local('docker-compose logs -f %s' % service)
  else:
    local('docker-compose logs -f')

@task
@runs_once
def docker_restart(service=''):
  """Restart Docker containers. Usage: fab docker_restart or fab docker_restart:service=web"""
  if service:
    local('docker-compose restart %s' % service)
  else:
    local('docker-compose restart')

@task
@runs_once
def docker_shell(service='web'):
  """Open shell in container. Usage: fab docker_shell:service=web"""
  local('docker-compose exec %s /bin/bash' % service)

@task
@runs_once
def docker_clean():
  """Remove stopped containers and dangling images"""
  local('docker-compose down -v')
  local('docker system prune -f')

@task
@roles('docker_remote')
def docker_deploy_remote():
  """Deploy to remote docker server"""
  # Create remote directory structure
  run('mkdir -p ~/docker/cigarbox/templates')
  run('mkdir -p ~/docker/cigarbox/static')
  run('mkdir -p ~/docker/cigarbox/nginx')
  run('mkdir -p ~/docker/cigarbox/logs')

  # Upload main files
  put('docker-compose.yml', '~/docker/cigarbox/docker-compose.yml')
  put('Dockerfile', '~/docker/cigarbox/Dockerfile')
  put('requirements.txt', '~/docker/cigarbox/requirements.txt')
  put('gunicorn_config.py', '~/docker/cigarbox/gunicorn_config.py')
  put('.env.example', '~/docker/cigarbox/.env.example')
  put('config.py', '~/docker/cigarbox/config.py')

  # Only upload photos.db if it has changed
  import hashlib
  local_hash = hashlib.md5(open('photos.db', 'rb').read()).hexdigest()
  remote_hash = run('test -f ~/docker/cigarbox/photos.db && md5sum ~/docker/cigarbox/photos.db | cut -d" " -f1 || echo "none"', quiet=True)
  if local_hash != remote_hash:
    print('Database changed, uploading...')
    put('photos.db', '~/docker/cigarbox/photos.db')
  else:
    print('Database unchanged, skipping upload')

  # Upload Python files
  for deployfile in deployfiles:
    put(deployfile+'.py', '~/docker/cigarbox/%s.py' % deployfile)

  # Upload test files
  put('run_tests.py', '~/docker/cigarbox/run_tests.py')
  put('test_*.py', '~/docker/cigarbox/')

  # Upload directories
  put('templates/*', '~/docker/cigarbox/templates/')
  put('nginx/*', '~/docker/cigarbox/nginx/')

  # Build and start
  with cd('~/docker/cigarbox'):
    # Stop any existing containers
    run('docker-compose down || true')

    # Always create fresh .env from .env.example
    run('cp .env.example .env')

    # Show what ports we're using
    run('echo "Using ports from .env:" && grep PORT .env')

    # Build and start containers
    run('docker-compose build')
    run('docker-compose up -d')
    run('docker-compose ps')

@task
@roles('docker_remote')
def docker_remote_logs(service=''):
  """View logs on remote docker server"""
  with cd('~/docker/cigarbox'):
    if service:
      run('docker-compose logs -f %s' % service)
    else:
      run('docker-compose logs -f')

@task
@roles('docker_remote')
def docker_remote_restart(service=''):
  """Restart containers on remote docker server"""
  with cd('~/docker/cigarbox'):
    if service:
      run('docker-compose restart %s' % service)
    else:
      run('docker-compose restart')
