#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CigarBox Fabric Deployment Tasks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fabric2 deployment automation for CigarBox photo management system.

Usage:
    fab --list                          # List all available tasks
    fab test                            # Run local unit tests
    fab deploy                          # Deploy to Docker test server
    fab deploy --role=prod              # Deploy to Docker production
    fab backup --role=prod              # Backup production database

:copyright: (c) 2015-2025 by Nathan Hubbard @n8foo.
:license: Apache, see LICENSE for more details.
"""

from fabric import task, Connection
from invoke import run as local
import time
import os
import hashlib
import yaml

# Configuration
DEPLOY_FILES = ["api", "app", "aws", "db", "process", "setup", "util", "web"]

# Deployment directories and files to include in tgz
DEPLOY_INCLUDES = [
    "*.py",
    "templates/",
    "static/",
    "tests/",
    "cli/",
    "scripts/",
    "nginx/*.conf",
    "requirements.txt",
    "docker-compose.yml",
    "docker-compose-prod.yml",
    "Dockerfile",
    "gunicorn_config.py",
    ".env.example",
    "run_tests.py",
]

# Load role-to-host mapping from fabric.yaml
def get_host_from_role(role):
    """Get hostname from role defined in fabric.yaml"""
    with open('fabric.yaml', 'r') as f:
        config = yaml.safe_load(f)
        return config['roles'][role]['host']


def get_compose_file(role):
    """Get the appropriate docker-compose file based on role

    Returns:
        str: docker-compose filename to use

    Production uses docker-compose-prod.yml (no nginx container)
    Test/dev uses docker-compose.yml (with nginx container)
    """
    if role == 'prod':
        return 'docker-compose-prod.yml'
    return 'docker-compose.yml'


def get_test_api_url():
    """Get test API URL from fabric.yaml or environment variable

    Returns:
        str: Test API URL (e.g., http://hostname:8088/api)
    """
    # Check environment variable first
    if 'CIGARBOX_TEST_API' in os.environ:
        return os.environ['CIGARBOX_TEST_API']

    # Try to read from fabric.yaml
    if os.path.exists('fabric.yaml'):
        try:
            with open('fabric.yaml', 'r') as f:
                config = yaml.safe_load(f)
                if 'roles' in config and 'test' in config['roles']:
                    test_host = config['roles']['test']['host']
                    return f'http://{test_host}:8088/api'
        except Exception as e:
            print(f'Warning: Could not read fabric.yaml: {e}')

    # Fall back to localhost
    return 'http://localhost:8088/api'


# =============================================================================
# Database Backup & Restore Tasks
# =============================================================================

@task
def backup(c, role='test'):
    """Backup remote database to local backups/ directory

    Args:
        role: Target role (test, prod)

    Usage:
        fab backup              # Backup test database
        fab backup --role=prod  # Backup prod database
    """
    timestamp = str(int(time.time()))
    host = get_host_from_role(role)

    local('mkdir -p backups')

    with Connection(host) as conn:
        remote_home = conn.run('echo $HOME', hide=True).stdout.strip()
        remote_db = f'{remote_home}/docker/cigarbox/photos.db'
        local_backup = f'backups/{role}-{timestamp}.db'

        conn.get(remote_db, local_backup)
        print(f'✓ Backup created: {local_backup}')


@task
def pushdb(c, role='test'):
    """Push local database to remote server

    Args:
        role: Target role (test, prod)

    Usage:
        fab pushdb              # Push to test
        fab pushdb --role=prod  # Push to prod (use with caution!)
    """
    host = get_host_from_role(role)

    if not os.path.exists('photos.db'):
        print('✗ Local photos.db not found')
        return

    # Backup first
    print('Creating backup before push...')
    backup(c, role=role)

    with Connection(host) as conn:
        remote_home = conn.run('echo $HOME', hide=True).stdout.strip()
        remote_db = f'{remote_home}/docker/cigarbox/photos.db'

        conn.put('photos.db', remote_db)
        print(f'✓ Database pushed to {role} ({host})')
        print('  Remember to restart containers: fab restart --role={role}')


@task
def pulldb(c, role='test'):
    """Pull database from remote server to local

    Args:
        role: Target role (test, prod)

    Usage:
        fab pulldb              # Pull from test
        fab pulldb --role=prod  # Pull from prod
    """
    host = get_host_from_role(role)

    with Connection(host) as conn:
        remote_home = conn.run('echo $HOME', hide=True).stdout.strip()
        remote_db = f'{remote_home}/docker/cigarbox/photos.db'

        conn.get(remote_db, 'photos.db')
        print(f'✓ Database pulled from {role} ({host})')


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
# Local Development & Testing Tasks
# =============================================================================

@task
def test(c):
    """Run tests locally against remote test server

    Reads test server hostname from fabric.yaml (test role) or CIGARBOX_TEST_API env var.
    Runs tests on your local machine, but integration tests connect to remote server.

    Usage:
        fab test                                    # Run all tests against test role
        CIGARBOX_TEST_API=http://host:8088/api fab test  # Override test server
    """
    test_api_url = get_test_api_url()
    print(f'🧪 Running tests locally against: {test_api_url}')

    # Set environment variable for integration tests
    env_with_api = f'CIGARBOX_TEST_API={test_api_url} python run_tests.py'
    local(env_with_api)


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
def deploy(c, role='test', package=None, rebuild=False, force_db=False):
    """Deploy to Docker server using tgz package

    Args:
        role: Target role (test, prod)
        package: Optional specific package file (defaults to building new one)
        rebuild: Force container rebuild (default False for fast deploys)
        force_db: Allow database upload (DANGEROUS for prod!)

    Usage:
        fab deploy                              # Fast deploy to test (no rebuild)
        fab deploy --role=prod                  # Fast deploy to prod
        fab deploy --rebuild                    # Full deploy with container rebuild
        fab deploy --package=deploys/cigarbox-1234567890.tar.gz  # Deploy specific package
        fab deploy --force-db                   # Upload database (USE WITH CAUTION!)
    """
    timestamp = str(int(time.time()))

    # Build package if not specified
    if not package:
        print('📦 Building deployment package...')
        package = build_package(c)

    package_basename = os.path.basename(package)
    host = get_host_from_role(role)

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

        # Handle photos.db separately
        # Database is NEVER uploaded automatically - must use --force-db
        if os.path.exists('photos.db'):
            local_hash = hashlib.md5(open('photos.db', 'rb').read()).hexdigest()
            result = conn.run(f'test -f {deploy_dir}/photos.db && md5sum {deploy_dir}/photos.db | cut -d" " -f1 || echo "none"', hide=True)
            remote_hash = result.stdout.strip()

            if local_hash != remote_hash:
                if not force_db:
                    print(f'⚠️  {role.upper()} database differs but not uploading (use --force-db to override)')
                    print(f'   Local:  {local_hash}')
                    print(f'   Remote: {remote_hash}')
                else:
                    # --force-db flag provided
                    if role == 'prod':
                        print('🚨 WARNING: About to upload database to PRODUCTION!')
                        print(f'   Local:  {local_hash}')
                        print(f'   Remote: {remote_hash}')
                        response = input('Type "yes" to continue: ')
                        if response.lower() != 'yes':
                            print('❌ Database upload cancelled')
                            return
                    else:
                        print(f'📦 Database changed, uploading to {role}...')
                        print(f'   Local:  {local_hash}')
                        print(f'   Remote: {remote_hash}')

                    conn.put('photos.db', f'{deploy_dir}/photos.db')
                    print(f'✓ Database uploaded to {role}')
            else:
                print('✓ Database unchanged, skipping upload')

        # Create logs directories with proper permissions for container user (UID 1000)
        print('📁 Setting up logs directory...')
        conn.run(f'mkdir -p {deploy_dir}/logs/nginx')
        # Use sudo for chmod since docker may have created these as root
        result = conn.run(f'sudo chmod -R 777 {deploy_dir}/logs', warn=True)
        if not result.ok:
            print('⚠️  Warning: Could not set log permissions (may need manual sudo chmod -R 777 ~/docker/cigarbox/logs)')

        # Build and start
        compose_file = get_compose_file(role)
        with conn.cd(deploy_dir):
            # Stop any existing containers
            conn.run(f'docker-compose -f {compose_file} down || true')

            # Create .env if it doesn't exist
            conn.run('test -f .env || cp .env.example .env')

            # Show what ports we're using
            conn.run('echo "Using ports from .env:" && grep PORT .env')

            # Build and start containers
            print(f'📦 Using {compose_file} for {role} environment')

            if rebuild:
                print('🔨 Rebuilding containers (this will take a few minutes)...')
                conn.run(f'docker-compose -f {compose_file} build --pull')
            else:
                print('⚡ Fast deploy: skipping container build (code is volume-mounted)')

            # Start/restart containers (picks up new code from volumes)
            conn.run(f'docker-compose -f {compose_file} up -d')
            conn.run(f'docker-compose -f {compose_file} ps')

    print(f'✓ Deployed {package_basename} to {role} ({host})')


@task
def rebuild(c, role='test'):
    """Rebuild Docker containers (use when requirements.txt changes)

    Args:
        role: Target role (test, prod)

    Usage:
        fab rebuild                    # Rebuild containers on test
        fab rebuild --role=prod        # Rebuild containers on prod

    Note: This rebuilds the Docker images. Use this when:
    - requirements.txt changes (new Python packages)
    - Dockerfile changes
    - System dependencies change
    For code-only changes, use 'fab deploy' (much faster)

    This automatically deploys latest code before rebuilding.
    """
    print(f'📋 Rebuild will: 1) Deploy latest code, 2) Rebuild containers')

    # Deploy first to get latest code
    deploy(c, role=role, rebuild=True)


@task
def restart(c, role='test', service=''):
    """Restart Docker containers on remote server

    Args:
        role: Target role (test, prod)
        service: Optional service name (web, api, nginx)

    Usage:
        fab restart                          # Restart all on test
        fab restart --service=api            # Restart API on test
        fab restart --role=prod --service=web  # Restart web on prod
    """
    host = get_host_from_role(role)
    compose_file = get_compose_file(role)
    with Connection(host) as conn:
        remote_home = conn.run('echo $HOME', hide=True).stdout.strip()
        deploy_dir = f'{remote_home}/docker/cigarbox'
        with conn.cd(deploy_dir):
            if service:
                conn.run(f'docker-compose -f {compose_file} restart {service}')
                print(f'✓ Restarted {service} on {role}')
            else:
                conn.run(f'docker-compose -f {compose_file} restart')
                print(f'✓ Restarted all services on {role}')


@task
def logs(c, role='test', service='', tail=50):
    """View Docker logs on remote server

    Args:
        role: Target role (test, prod)
        service: Optional service name (web, api, nginx)
        tail: Number of lines to show (default 50)

    Usage:
        fab logs                              # Show all logs
        fab logs --service=api                # Show API logs
        fab logs --service=web --tail=100     # Show 100 lines
    """
    host = get_host_from_role(role)
    compose_file = get_compose_file(role)
    with Connection(host) as conn:
        remote_home = conn.run('echo $HOME', hide=True).stdout.strip()
        deploy_dir = f'{remote_home}/docker/cigarbox'
        with conn.cd(deploy_dir):
            if service:
                conn.run(f'docker-compose -f {compose_file} logs --tail={tail} {service}')
            else:
                conn.run(f'docker-compose -f {compose_file} logs --tail={tail}')


@task
def status(c, role='test'):
    """Check Docker container status on remote server

    Args:
        role: Target role (test, prod)

    Usage: fab status --role=test
    """
    host = get_host_from_role(role)
    compose_file = get_compose_file(role)
    with Connection(host) as conn:
        remote_home = conn.run('echo $HOME', hide=True).stdout.strip()
        deploy_dir = f'{remote_home}/docker/cigarbox'
        with conn.cd(deploy_dir):
            print(f'\n📊 Container Status on {role} ({host}):')
            conn.run(f'docker-compose -f {compose_file} ps')


@task
def test_remote(c, role='test'):
    """Run tests on remote Docker server (inside the container)

    Args:
        role: Target role (test, prod)

    Usage:
        fab test-remote              # Run tests on test server
        fab test-remote --role=prod  # Run tests on prod server
    """
    host = get_host_from_role(role)
    compose_file = get_compose_file(role)

    with Connection(host) as conn:
        remote_home = conn.run('echo $HOME', hide=True).stdout.strip()
        deploy_dir = f'{remote_home}/docker/cigarbox'
        with conn.cd(deploy_dir):
            print(f'🧪 Running tests on {role} ({host}) inside container...')
            conn.run(f'docker-compose -f {compose_file} exec -T web python run_tests.py')


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
def list_backups(c, role='test'):
    """List available backups on remote server

    Args:
        role: Target role (test, prod)

    Usage: fab list-backups --role=test
    """
    host = get_host_from_role(role)
    with Connection(host) as conn:
        remote_home = conn.run('echo $HOME', hide=True).stdout.strip()
        backups_dir = f'{remote_home}/docker/backups'
        result = conn.run(f'ls -lht {backups_dir}/', warn=True)
        if result.ok:
            print(f'💾 Available backups on {role} ({host}):')
        else:
            print(f'No backups found on {role} ({host})')


@task
def rollback(c, role='test', backup=None):
    """Rollback to a previous backup on remote server

    Args:
        role: Target role (test, prod)
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
    host = get_host_from_role(role)
    compose_file = get_compose_file(role)

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
            conn.run(f'docker-compose -f {compose_file} down || true')

        # Clear deployment directory (except .env and photos.db)
        conn.run(f'cd {deploy_dir} && find . -maxdepth 1 ! -name . ! -name .env ! -name photos.db -exec rm -rf {{}} +')

        # Extract backup
        print(f'📂 Restoring from backup: {backup}')
        conn.run(f'cd {deploy_dir} && tar xzf {backups_dir}/{backup}')

        # Restart containers
        with conn.cd(deploy_dir):
            conn.run(f'docker-compose -f {compose_file} build --pull')
            conn.run(f'docker-compose -f {compose_file} up -d')
            conn.run(f'docker-compose -f {compose_file} ps')

    print(f'✓ Rolled back to {backup} on {role} ({host})')


@task
def test_integration(c, role='test', port=8088):
    """Run integration tests against remote Docker deployment

    Args:
        role: Target role (test, prod)
        port: HTTP port (default 8088)

    Usage:
        fab test-integration                    # Test test server on port 8088
        fab test-integration --role=prod --port=8088
    """
    host = get_host_from_role(role)
    urls = ['/', '/photostream', '/tags', '/tags/misc', '/photosets', '/photosets/1068', '/photosets/1010/page/2']
    for url in urls:
        local(f'curl -sS -vL http://{host}:{port}{url} -o /dev/null')
