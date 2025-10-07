#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CigarBox Fabric Deployment Tasks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fabric2 deployment automation for CigarBox photo management system.

Usage:
    fab --list                          # List all available tasks
    fab test                            # Run local unit tests
    fab docker-deploy                   # Deploy to Docker test server (testserver)
    fab backup                          # Backup EC2 production database
    fab deploy --host=crank            # Deploy to Docker production (future)

:copyright: (c) 2015-2025 by Nathan Hubbard @n8foo.
:license: Apache, see LICENSE for more details.
"""

from fabric import task, Connection
from invoke import run as local
import time
import os
import hashlib

# Configuration
DEPLOY_FILES = ["api", "app", "aws", "db", "process", "setup", "util", "web"]

# Deployment directories and files to include in tgz
DEPLOY_INCLUDES = [
    "*.py",
    "templates/",
    "static/",
    "nginx/*.conf",
    "requirements.txt",
    "docker-compose.yml",
    "Dockerfile",
    "gunicorn_config.py",
    ".env.example",
    "run_tests.py",
    "test_*.py",
]

# Host shortcuts
DOCKER_TEST_HOST = "testserver"  # Test deployment
DOCKER_PROD_HOST = "crank"   # Future production
EC2_HOST = "cigarbox"        # Current EC2 production


# =============================================================================
# EC2 Production Tasks (legacy monit deployment)
# =============================================================================

@task
def backup(c):
    """Backup production database to timestamped SQL file"""
    local(f'echo .dump | sqlite3 photos.db | gzip -c > backups/{TIMESTAMP}.sql.gz')
    with Connection(EC2_HOST) as conn:
        conn.run('mkdir -p ~/cigarbox/backups')
        conn.put(f'backups/{TIMESTAMP}.sql.gz', f'~/cigarbox/backups/{TIMESTAMP}.sql.gz')
    print(f'✓ Backup created: {TIMESTAMP}.sql.gz')


@task
def pushdb(c):
    """Push local database to EC2 production (with backup)"""
    backup(c)
    with Connection(EC2_HOST) as conn:
        conn.put('photos.db', '~/cigarbox/photos.db')
        conn.run('sudo /etc/init.d/cigarbox restart')
    print('✓ Database pushed and service restarted')


@task
def pulldb(c):
    """Pull database from EC2 production to local"""
    with Connection(EC2_HOST) as conn:
        conn.get('~/cigarbox/photos.db', 'photos.db')
    print('✓ Database pulled from production')


@task
def restore(c, filename):
    """Restore database from backup file

    Args:
        filename: Backup file in backups/ directory (e.g., 1234567890.sql.gz)

    Usage: fab restore --filename=1234567890.sql.gz
    """
    backup_path = f'backups/{filename}'
    if not os.path.exists(backup_path):
        print(f'✗ Backup file not found: {backup_path}')
        return

    local(f'gunzip -c {backup_path} | sqlite3 photos.db')
    print(f'✓ Database restored from {filename}')


# =============================================================================
# Local Development Tasks
# =============================================================================

@task
def test(c):
    """Run unit tests locally"""
    local('python run_tests.py')


@task
def server(c):
    """Start local development web server on port 9600"""
    local('python web.py')


@task
def apiserver(c):
    """Start local development API server on port 9601"""
    local('python api.py')


@task
def cleanup(c):
    """Remove Python cache files and temporary data"""
    local('find . -type f -name "*.pyc" -delete')
    local('find . -type d -name "__pycache__" -delete')
    print('✓ Cleaned up Python cache files')


# =============================================================================
# Docker Local Tasks
# =============================================================================

@task
def docker_build(c):
    """Build Docker images locally"""
    local('docker build -f Dockerfile -t cigarbox:latest .')


@task
def docker_up(c):
    """Start Docker containers locally"""
    if not os.path.exists('.env'):
        local('cp .env.example .env')
        print('Created .env from .env.example - please review and customize')
    local('docker-compose up -d')
    local('docker-compose ps')


@task
def docker_down(c):
    """Stop Docker containers locally"""
    local('docker-compose down')


@task
def docker_logs(c, service=''):
    """View Docker logs locally

    Args:
        service: Optional service name (web, api, nginx)

    Usage: fab docker-logs --service=web
    """
    if service:
        local(f'docker-compose logs -f {service}')
    else:
        local('docker-compose logs -f')


@task
def docker_restart(c, service=''):
    """Restart Docker containers locally

    Args:
        service: Optional service name (web, api, nginx)

    Usage: fab docker-restart --service=api
    """
    if service:
        local(f'docker-compose restart {service}')
    else:
        local('docker-compose restart')


@task
def docker_shell(c, service='web'):
    """Open shell in Docker container

    Args:
        service: Service name (web, api, nginx)

    Usage: fab docker-shell --service=web
    """
    local(f'docker-compose exec {service} /bin/sh')


@task
def docker_clean(c):
    """Remove stopped containers and dangling images"""
    local('docker-compose down -v')
    local('docker system prune -f')


# =============================================================================
# Docker Remote Deployment Tasks
# =============================================================================

@task
def build_package(c):
    """Build deployment package as timestamped tgz in deploys/ directory

    Usage: fab build-package
    """
    timestamp = str(int(time.time()))

    # Create deploys directory if needed
    local('mkdir -p deploys')

    # Build tar command with all includes
    tar_includes = ' '.join(DEPLOY_INCLUDES)
    package_name = f'deploys/cigarbox-{timestamp}.tar.gz'

    local(f'tar czf {package_name} {tar_includes}')
    print(f'✓ Created deployment package: {package_name}')
    return package_name


@task
def deploy(c, host=DOCKER_TEST_HOST, package=None):
    """Deploy to Docker server using tgz package

    Args:
        host: Target host (testserver or crank)
        package: Optional specific package file (defaults to building new one)

    Usage:
        fab deploy                              # Build and deploy to test
        fab deploy --host=crank                 # Build and deploy to prod
        fab deploy --package=deploys/cigarbox-1234567890.tar.gz  # Deploy specific package
    """
    timestamp = str(int(time.time()))

    # Build package if not specified
    if not package:
        print('📦 Building deployment package...')
        package = build_package(c)

    package_basename = os.path.basename(package)

    with Connection(host) as conn:
        remote_home = conn.run('echo $HOME', hide=True).stdout.strip()
        deploy_dir = f'{remote_home}/docker/cigarbox'
        deploys_dir = f'{remote_home}/docker/deploys'
        backups_dir = f'{remote_home}/docker/backups'

        # Create directory structure
        conn.run(f'mkdir -p {deploy_dir}')
        conn.run(f'mkdir -p {deploys_dir}')
        conn.run(f'mkdir -p {backups_dir}')

        # Backup existing deployment if it exists
        result = conn.run(f'test -d {deploy_dir} && ls {deploy_dir}', warn=True, hide=True)
        if result.ok and result.stdout.strip():
            print(f'💾 Backing up existing deployment...')
            conn.run(f'cd {deploy_dir} && tar czf {backups_dir}/cigarbox-backup-{timestamp}.tar.gz .')
            print(f'✓ Backup created: {backups_dir}/cigarbox-backup-{timestamp}.tar.gz')

        # Upload new deployment package
        print(f'📤 Uploading {package_basename}...')
        conn.put(package, f'{deploys_dir}/{package_basename}')

        # Extract package
        print(f'📂 Extracting deployment...')
        conn.run(f'cd {deploy_dir} && tar xzf {deploys_dir}/{package_basename}')

        # Handle photos.db separately (don't overwrite on deploy)
        if os.path.exists('photos.db'):
            local_hash = hashlib.md5(open('photos.db', 'rb').read()).hexdigest()
            result = conn.run(f'test -f {deploy_dir}/photos.db && md5sum {deploy_dir}/photos.db | cut -d" " -f1 || echo "none"', hide=True)
            remote_hash = result.stdout.strip()

            if local_hash != remote_hash:
                print('📦 Database changed, uploading...')
                conn.put('photos.db', f'{deploy_dir}/photos.db')
            else:
                print('✓ Database unchanged, skipping upload')

        # Build and start
        with conn.cd(deploy_dir):
            # Stop any existing containers
            conn.run('docker-compose down || true')

            # Create .env if it doesn't exist
            conn.run('test -f .env || cp .env.example .env')

            # Show what ports we're using
            conn.run('echo "Using ports from .env:" && grep PORT .env')

            # Build and start containers
            conn.run('docker-compose build --pull')
            conn.run('docker-compose up -d')
            conn.run('docker-compose ps')

    print(f'✓ Deployed {package_basename} to {host}')


@task
def restart(c, host=DOCKER_TEST_HOST, service=''):
    """Restart Docker containers on remote server

    Args:
        host: Target host (testserver or crank)
        service: Optional service name (web, api, nginx)

    Usage:
        fab restart                          # Restart all on test
        fab restart --service=api            # Restart API on test
        fab restart --host=crank --service=web  # Restart web on prod
    """
    with Connection(host) as conn:
        remote_home = conn.run('echo $HOME', hide=True).stdout.strip()
        deploy_dir = f'{remote_home}/docker/cigarbox'
        with conn.cd(deploy_dir):
            if service:
                conn.run(f'docker-compose restart {service}')
                print(f'✓ Restarted {service} on {host}')
            else:
                conn.run('docker-compose restart')
                print(f'✓ Restarted all services on {host}')


@task
def logs(c, host=DOCKER_TEST_HOST, service='', tail=50):
    """View Docker logs on remote server

    Args:
        host: Target host (testserver or crank)
        service: Optional service name (web, api, nginx)
        tail: Number of lines to show (default 50)

    Usage:
        fab logs                              # Show all logs
        fab logs --service=api                # Show API logs
        fab logs --service=web --tail=100     # Show 100 lines
    """
    with Connection(host) as conn:
        remote_home = conn.run('echo $HOME', hide=True).stdout.strip()
        deploy_dir = f'{remote_home}/docker/cigarbox'
        with conn.cd(deploy_dir):
            if service:
                conn.run(f'docker-compose logs --tail={tail} {service}')
            else:
                conn.run(f'docker-compose logs --tail={tail}')


@task
def status(c, host=DOCKER_TEST_HOST):
    """Check Docker container status on remote server

    Args:
        host: Target host (testserver or crank)

    Usage: fab status --host=testserver
    """
    with Connection(host) as conn:
        remote_home = conn.run('echo $HOME', hide=True).stdout.strip()
        deploy_dir = f'{remote_home}/docker/cigarbox'
        with conn.cd(deploy_dir):
            print(f'\n📊 Container Status on {host}:')
            conn.run('docker-compose ps')


@task
def test_remote(c, host=DOCKER_TEST_HOST):
    """Run unit tests on remote Docker server

    Args:
        host: Target host (testserver or crank)

    Usage: fab test-remote
    """
    with Connection(host) as conn:
        remote_home = conn.run('echo $HOME', hide=True).stdout.strip()
        deploy_dir = f'{remote_home}/docker/cigarbox'
        with conn.cd(deploy_dir):
            conn.run('docker-compose exec -T web python run_tests.py')


@task
def list_deploys(c):
    """List available local deployment packages

    Usage: fab list-deploys
    """
    if os.path.exists('deploys'):
        result = local('ls -lht deploys/', hide=True)
        print('📦 Available local deployment packages:')
        print(result.stdout)
    else:
        print('No deploys/ directory found')


@task
def list_backups(c, host=DOCKER_TEST_HOST):
    """List available backups on remote server

    Args:
        host: Target host (testserver or crank)

    Usage: fab list-backups --host=testserver
    """
    with Connection(host) as conn:
        remote_home = conn.run('echo $HOME', hide=True).stdout.strip()
        backups_dir = f'{remote_home}/docker/backups'
        result = conn.run(f'ls -lht {backups_dir}/', warn=True)
        if result.ok:
            print(f'💾 Available backups on {host}:')
        else:
            print(f'No backups found on {host}')


@task
def rollback(c, host=DOCKER_TEST_HOST, backup=None):
    """Rollback to a previous backup on remote server

    Args:
        host: Target host (testserver or crank)
        backup: Backup filename (e.g., cigarbox-backup-1234567890.tar.gz)

    Usage:
        fab list-backups                    # See available backups
        fab rollback --backup=cigarbox-backup-1234567890.tar.gz
    """
    if not backup:
        print('❌ Error: Must specify --backup=filename')
        print('Run "fab list-backups" to see available backups')
        return

    timestamp = str(int(time.time()))

    with Connection(host) as conn:
        remote_home = conn.run('echo $HOME', hide=True).stdout.strip()
        deploy_dir = f'{remote_home}/docker/cigarbox'
        backups_dir = f'{remote_home}/docker/backups'

        # Verify backup exists
        result = conn.run(f'test -f {backups_dir}/{backup}', warn=True)
        if not result.ok:
            print(f'❌ Error: Backup not found: {backups_dir}/{backup}')
            print('Run "fab list-backups" to see available backups')
            return

        # Backup current state before rollback
        print(f'💾 Backing up current deployment before rollback...')
        conn.run(f'cd {deploy_dir} && tar czf {backups_dir}/cigarbox-pre-rollback-{timestamp}.tar.gz .')

        # Stop containers
        with conn.cd(deploy_dir):
            conn.run('docker-compose down || true')

        # Clear deployment directory (except .env and photos.db)
        conn.run(f'cd {deploy_dir} && find . -maxdepth 1 ! -name . ! -name .env ! -name photos.db -exec rm -rf {{}} +')

        # Extract backup
        print(f'📂 Restoring from backup: {backup}')
        conn.run(f'cd {deploy_dir} && tar xzf {backups_dir}/{backup}')

        # Restart containers
        with conn.cd(deploy_dir):
            conn.run('docker-compose build --pull')
            conn.run('docker-compose up -d')
            conn.run('docker-compose ps')

    print(f'✓ Rolled back to {backup} on {host}')


@task
def test_integration(c, host=DOCKER_TEST_HOST, port=8088):
    """Run integration tests against remote Docker deployment

    Args:
        host: Target host (testserver or crank)
        port: HTTP port (default 8088)

    Usage:
        fab test-integration                    # Test testserver:8088
        fab test-integration --host=crank --port=8088
    """
    urls = ['/', '/photostream', '/tags', '/tags/misc', '/photosets', '/photosets/1068', '/photosets/1010/page/2']
    for url in urls:
        local(f'curl -sS -vL http://{host}:{port}{url} -o /dev/null')
