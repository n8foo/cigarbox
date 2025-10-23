# CigarBox Changelog

All notable changes to this project are documented here.

## [2025-10-22]

### Added
- **API authentication system** with simple API key validation
- **Enhanced CLI upload tool** (cli/upload.py)
  - Configurable rate limiting with --delay parameter (default 0.1s)
  - Improved error handling with detailed error messages
- **Deployment safety improvements**

### Changed
- **Simplified requirements.txt** 
- Updated test suite to work with API authentication
- Added volume mounts for tests/ and security.py to Docker containers

### Fixed
- Fixed subpath URL generation in templates for proper relative path resolution
- Updated URL generation in layout.html, photos.html, photoset.html, photosets.html, photostream.html, tag_cloud.html, and photo_in_photoset.html
- Corrected get_base_url() usage in web.py for consistent URL handling
- Added config.py.example with configuration template
- Added docker-compose-prod.yml for production deployment (2-container architecture without nginx)

## [2025-10-21]

### Changed
- **Reorganized codebase structure** for better modularity
  - Moved CLI tools to `cli/` directory (import.py, upload.py, photo_checker.py)
  - Renamed setup.py to init_db.py (avoids Python package naming conflicts)
  - Moved all tests to `tests/` directory
- **Updated Fabric deployment to role-based system**
  - Role-based deployment commands with `--role=test|prod` flags
  - Removed hardcoded server hostnames, now using fabric.yaml configuration
  - Added `fab rebuild` task for container updates when dependencies change
  - Updated test runner to discover tests from tests/ directory
- fabric.yaml is now single source of truth for server configuration

## [2025-10-08]
- Added get_pagination_data() helper function
- Added pagination to all appropriate pages
- Using bootstraps pagination bits

## [2025-10-07]

### Changed
- **Migrated to Fabric2** from Fabric3 for modern Python 3 support with paramiko 3.5.0
- **Rewrote deployment system** to use tgz-based packages with automatic backups and rollback capability
  - Timestamped packages in `deploys/`, automatic remote backups to `~/docker/backups/`
  - Database and `.env` preserved across deployments (MD5 validation for changed files only)
  - New commands: `fab build-package`, `fab list-deploys`, `fab list-backups`, `fab rollback`, `fab test-integration`
  - Simplified core commands: `fab deploy`, `fab restart`, `fab logs`, `fab status`
  - Removed deprecated docker_*_remote tasks

### Fixed
- Upgraded Flask-WTF (1.0.1→1.2.1), Werkzeug (2.x→3.0.6), Flask-Login (0.6.0→0.6.3), requests-toolbelt (0.9.1→1.0.0)
- Updated Pillow API to use `Image.Resampling.LANCZOS` instead of deprecated `ANTIALIAS` (util.py:47)
- All 65 unit and integration tests now passing


## [2025-10-06]

### Added
- Docker deployment with 3-container architecture (web, api, nginx)
- Nginx reverse proxy with rate limiting and security headers
- Gunicorn production server with proper port binding
- Health checks for Flask applications
- Integration tests for upload.py CLI tool (6 tests)
- Fabric tasks for remote Docker deployment and debugging
- Environment configuration via .env files
- Optimized database syncing with MD5 checksum validation
- Documentation for photo_checker.py utility

### Fixed
- Critical race condition with datetime.datetime.now() in database models
- Database query bugs with missing table prefixes
- Logic errors in web routes and error handlers
- AWS S3 key deletion method call
- GPS coordinate bounds checking in EXIF processing
- Upload.py import issues with argparse
- Docker container permissions for /tmp/cigarbox
- API and web healthcheck port configurations
- Unit test assertions for string normalization and redirects

### Changed
- All 65 tests now passing (59 unit + 6 integration)
- Updated requirements.txt for Python 3.9 compatibility
- Separated web and API containers with proper port binding
- ProxyFix middleware for proper URL generation behind nginx

## [2022-07-06]

### Added
- Additional API calls for tags and photosets
- Support for updates without file upload (via photo_id)

## [2022-06-27]

### Changed
- Python 3 migration continued
- Additional Python 3 compatibility fixes

## [2022-06-26]

### Security
- Updated Pillow from 9.1.0 to 9.1.1 (Dependabot)

## [2022-05-01]

### Changed
- First pass at Python 3 migration

## [2021-09-07]

### Security
- Updated Pillow from 2.7.0 to 8.3.2 (Dependabot)

## [2021-03-19]

### Security
- Updated Jinja2 from 2.7.3 to 2.11.3 (Dependabot)

## [2020-05-27]

### Security
- Updated requests from 2.5.1 to 2.20.0 (Dependabot)
- Updated paramiko from 1.15.2 to 2.0.9 (Dependabot)
- Updated werkzeug from 0.10.1 to 0.15.3 (Dependabot)
- Updated gunicorn from 18.0 to 19.5.0 (Dependabot)
- Updated Flask from 0.10.1 to 1.0 (Dependabot)
- Updated ecdsa from 0.13 to 0.13.3 (Dependabot)

## [2020-05-26]

### Added
- Support for checking prior upload via API
- Tagging functionality via API

## [2020-05-24]

### Added
- SHA1 hash verification and search
- Various improvements and bug fixes

## [2016-12-30]

### Fixed
- Import metadata now stores client-side filename instead of temporary server filename

## [2016-12-29]

### Added
- SHA1 search function
- Date display and search for photos
- Cleanup and logging improvements

### Changed
- Updated Bootstrap to 3.3.6
- Cleaner database class implementation
- Error message improvements

## [2016-01-24]

### Removed
- Flask-Peewee dependency (replaced with plain Peewee)

## [2016-01-16]

### Changed
- Database schema cleanup
- Migration scripts verification

## [2016-01-03]

### Added
- Photoset support
- SHA1 verification for uploads

### Changed
- Port changed to 9000 range (9600 web, 9601 api)

## [2015-03-25]

### Added
- Tag support at upload time
- Bootstrap-based upload form
- Manual upload to web interface
- First version of upload API and client
- Separated image processing functions

## [2015-03-08]

### Added
- S3 delete functionality

### Changed
- Updated to Bootstrap 3.3.2
- Library updates

## [2015-02-19]

### Added
- Photoset deletion capabilities

## [2014-06-23]

### Changed
- Moved config.py to config.example
- Added config.py to .gitignore

## [2014-06-13]

### Changed
- Replaced custom auth with Flask-Security

## [2014-06-12]

### Fixed
- Privacy setting bug

### Changed
- Moved to flat organization layout
- Separated code into modules
- Prepared for Flask-Peewee and Flask-Security integration

## [2014-06-13]

### Changed
- Replaced custom auth with Flask-Security

## [2014-06-12]

### Fixed
- Privacy setting bug

### Changed
- Moved to flat organization layout
- Separated code into modules
- Prepared for Flask-Peewee and Flask-Security integration

## [2014-06-11]

### Added
- Tag deletion functionality
- Layout fixes for URLs

## [2014-05-30]

### Changed
- Converted import.py to use Peewee ORM
- Fixed original display bug with class scope

## [2014-05-29]

### Changed
- Web app migrated to Peewee ORM
- Removed old pagination usage

## [2014-05-28]

### Added
- Initial Peewee ORM implementation

## [2014-03-23]

### Added
- Basic Twitter card support
- requirements.txt file

## [2014-03-10]

### Added
- README and About page updates

### Fixed
- Various bugs for production deployment
- Template updates for real server deployment

## [2014-03-08]

### Added
- Nag bar for important notifications
- Photoset thumbnail display

## [2014-03-04]

### Added
- Support for protected/challenge originals
- Private ACL as default for originals

## [2014-03-03]

### Added
- Privacy flag support
- Basic pagination

### Changed
- EXIF processing 2.5x faster using Pillow/PIL (ExifRead no longer required)
- Fixed date storage, moved fileDate to import_meta

## [2014-02-26]

### Changed
- Moved to common database functions
- Photosets now have titles
- Import metadata split back into main()

## [2014-02-24]

### Added
- Function to check S3 import status
- Template cleanup

## [2014-02-22]

### Added
- Import metadata support

## [2014-02-17]

### Added
- Set creation based on parent directory option
- Batch thumbnail generation
- AWS S3 upload support

### Changed
- Better logging throughout
- Thumbnail regeneration options
- Generate all thumbnail sizes properly
- More flexible thumbnail generation (S3 related)
- Cleaner database statements
- Template updates with Bootstrap (CDN)

## [2014-02-16]

### Added
- AWS S3 upload support
- Config file implementation

### Changed
- Moved more functionality into utility library
- Removed config from main code

## [2014-02-11]

### Added
- Better tag support and tag browsing via /tag/<tag>

### Changed
- Thumbnail quality boost
- Moved to shorter filenames (dirpath removed from sha1 length)
- Photos in descending order

## [2014-02-10]

### Added
- Photo sets support
- Unique indexes
- Skip thumbnail generation if exists, with regen option

### Changed
- Better tag handling
- SQL cleanup
- Thumbnail generation preserves ICC profile
- Template improvements

## [2014-02-09]

### Added
- Thumbnail generation
- Photo detail view at /photos/<id>
- Instructions and documentation

### Changed
- Web UI now actually useful
- Template updates

## [2014-02-08]

### Added
- ImportMeta table for archive metadata preservation
- Base58 functions for short URLs
- Tag cloud
- Photo links
- Utility module
- Config file usage

### Changed
- More modular code organization
- Alignment fixes

## [2014-02-07]

### Added
- Web front end with templates
- Additional import updates

### Changed
- Name updates throughout
- Flickr-like API structure
- README updates

## [2014-02-06]

### Changed
- More Flickr-inspired updates

## [2014-02-05]

### Added
- New file structure
- Flickr-like API approach

### Fixed
- SHA1 implementation
- EXIF handling for missing dates

## [2014-02-02]

### Added
- Database schema
- .gitignore for database file

## [2014-01-30]

### Added
- Initial commit - Project started
