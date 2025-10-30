# CigarBox Changelog

All notable changes to this project are documented here.

---
## [2025-10-30] - UI Improvements and Navigation Enhancements

### Added
- **Keyboard shortcuts for photo page**
  - Arrow keys (←/→) for photo navigation, (↑) for back to context
  - `t` to edit tags, `p` for privacy, `s` to share, `o` for original
  - `Delete` key to delete photo, `?` to show keyboard help
  - `Esc` to close modals
  - Respects browser shortcuts (Alt/Cmd/Ctrl combinations)
  - Auto-focus on input fields when modals open

- **Keyboard shortcuts for photoset page**
  - `s` to share photoset, `e` for bulk edit
  - Respects browser shortcuts (Alt/Cmd/Ctrl combinations)

- **Photoset metadata display (Icon Metadata Bar pattern)**
  - Date range of photos in set (e.g., "2024-01-15 to 2024-03-20")
  - Shows single date if all photos from same day
  - All unique tags across photoset photos (clickable)
  - Date with calendar icon displayed under description

- **Share count badges**
  - Red notification badges on Share buttons (photos and photosets)
  - Shows count only when shares exist
  - Clicking badge navigates to admin shares with search pre-filled

- **Context-aware navigation for tags and dates**
  - Tag pages now pass `?context=tag:name` to photo links
  - Date pages pass `?context=date:YYYY-MM-DD`
  - Enables prev/next navigation within tag/date contexts

- **Photoset breadcrumb shows photoset title**
  - When viewing photo from photoset context, breadcrumb shows actual photoset name
  - e.g., "Vacation 2024 / Photo #123" instead of "Photoset / Photo #123"

### Changed
- **Photo page header redesign (Icon Metadata Bar pattern)**
  - Header split 50/50 (col-md-6 / col-md-6) for better space efficiency
  - Photo ID with date and time inline in breadcrumb
  - Photosets list below breadcrumb (filters out current context photoset)
  - Tags displayed in right column with icon
  - All action buttons in right column header
  - Icon-based button style matching photoset pages
  - Removed duplicate details section below photo

- **Photoset page enhancements**
  - Delete button moved to edit modal footer (progressive disclosure)
  - Date displayed under description instead of in action area
  - Tags moved to right column for cleaner layout
  - Removed "Active Shares" collapsible panel

- **Share management improvements**
  - Replaced collapsible share panels with notification badges
  - Admin shares page now shows both photos and photosets
  - Added Comment column to shares table
  - Action buttons use icons only (copy, revoke) for compact display

- **Fabric logs command simplified**
  - Removed confusing flags, now shows all logs by default
  - Docker logs + application log + nginx logs (prod)
  - New `fab follow-logs` command for live streaming
  - 100 lines per log source (configurable with `--tail`)

### Fixed
- **Photoset date range logic**
  - Single date shown when all photos from same day
  - Compares date strings instead of datetime objects
- **Keyboard shortcuts respect browser navigation**
  - Arrow keys with modifiers (Alt/Cmd/Ctrl) no longer intercepted
- **Admin shares query includes photoset shares**
  - Changed to LEFT OUTER JOIN to show all share types
  - Search works for photo ID, photoset ID, or token
- **Header whitespace optimization**
  - Tighter margins on date and photoset displays
  - Reduced vertical spacing in photo and photoset headers
  - Better use of above-the-fold space

---
## [2025-10-29] - Navigation Performance Optimization

### Performance
- **Optimized photo navigation queries** (387x faster for photostream)
  - Replaced memory-loading approach with SQL adjacent lookups
  - Before: Load all 42K photos into list, linear search (839ms)
  - After: Two indexed SQL queries with LIMIT 1 (2.16ms)
  - Affects all contexts: photostream, photosets, tags, dates
  - Also optimized shared photoset navigation

- **Added database index on privacy column**
  - Created `idx_photo_privacy` index on `photo(privacy)`
  - Speeds up all privacy-filtered queries
  - Migration: `scripts/migrate_2025_10_29_add_privacy_index.py`

### Added
- **Performance testing suite** in `perf/` directory
  - `perf_test_navigation.py` - Measure query execution times
  - `analyze_privacy_query.py` - Analyze query plans and index usage

### Changed
- `web.py` - Replaced list materialization with SQL lookups in:
  - `show_photo()` function (lines 213-324)
  - `view_shared_photoset_photo()` function (lines 1956-1997)

---
## [2025-10-29] - Photo Sharing System & Navigation

### Added
- **Unified photo and photoset sharing system**
  - Single ShareToken table handles both photos and photosets
  - Share comments/metadata for tracking who/why shares were created
  - Download original toggle (uses signed S3 URLs)
  - Max views limit (NULL = unlimited)
  - View tracking with detailed logging (IP, user agent, comment)
  - Share management UI on photo and photoset pages (collapsible panels)
  - Inline revoke capability with AJAX
  - Copy-to-clipboard for share URLs

- **Context-aware photo navigation**
  - Prev/Next buttons when viewing photos
  - Maintains context: photostream, photosets, tags, dates
  - Breadcrumb navigation showing current context
  - "Back to [Context]" button for easy return

- **Keyboard navigation**
  - Arrow keys (← →) to navigate between photos
  - Works in regular photos and shared photosets
  - Disabled when typing in form fields

- **Enhanced shared photoset viewing**
  - Individual photo pages (not direct S3 links)
  - Full-size photo display with navigation
  - Download button on photo page (if enabled)
  - Breadcrumb back to photoset grid

### Fixed
- **Jinja template syntax error** in photos.html (duplicate endif)
- **S3 download access** - Use signed URLs for private originals instead of direct links
- **Missing share URL display** for photoset shares (added success alert with copy button)

### Changed
- Photo page now includes navigation context from referrer
- Photostream and photoset grids link with context parameters
- Share creation includes comment, max views, and download options

---
## [2025-10-28] - Photosets Privacy Fix

### Fixed
- **Empty photosets appearing for logged-out users**
  - Photosets with only private photos no longer show in list view
  - Uses efficient JOIN with GROUP BY to find photosets with visible photos
  - Bulk-fetches all thumbnails in single query (3 total queries vs N+2)
  - Pagination counts now accurate after filtering

---
## [2025-10-27] - Upload & Delete Improvements

### Added
- **Per-file upload system** - Sequential file uploads instead of single multi-file request
  - Real-time per-file progress tracking with success/failure status
  - Better error handling for partial upload failures
  - Keeps upload size at 16MB max per file
- **Inline photoset creation** in bulk-edit interface
  - "+ Create New Photoset" option with inline input field
  - Backend creates photoset when `__new__` selected with title
- **Enhanced logging capabilities**
  - `--follow` flag for live log streaming (tail -f style)
  - `-n` alias for `--tail` parameter
  - Renamed `--show-all` to `--all` for consistency
- **Nginx config checker** - `fab check-nginx-config` task compares local vs remote configs

### Changed
- Upload interface now sends files individually with per-file progress

### Fixed
- **Photo deletion CASCADE failures**
  - Manually delete all relationships (PhotoTag, PhotoPhotoset, ImportMeta, ShareToken)
  - Added detailed logging for each deletion step
  - Added try/catch with user-facing error messages
  - Prevents FOREIGN KEY constraint errors on delete

## [2025-10-25] - Admin Tools & Data Integrity

### Added
- **Admin Tools Dashboard** at `/admin/tools` with unified navigation
- **Migration Runner** - Web UI to run database migrations from `scripts/` directory
  - Shows migration history with success/failure status and timestamped logs in `logs/migrations/`
  - Idempotent migrations safe to re-run multiple times
- **Data Audit Tools** with pagination (100 items/page) and shift-click range selection
  - Missing dates audit: Find and fix photos with NULL `datetaken`
  - Orphaned ImportMeta audit: Find and delete orphaned metadata records
  - Clickable file dates linking to date search pages
- **Development workflow tools**
  - `fab dev` - Single command runs both web and API with combined output
  - `fab watch-logs` - Tail shared cigarbox.log locally
  - `fab logs --app-log` - View application logs on remote server
- **Unified admin navigation** template (`admin/admin_base.html`) with Tools tab
- Migration script: `scripts/migrate_2025_10_25_cascade_deletes.py` (idempotent)

### Changed
- **CASCADE delete constraints** on Photo relationships (PhotoTag, PhotoPhotoset, ShareToken)
  - Prevents orphaned relationship records when photos are deleted
  - Prevents ID reuse issues where deleted photo IDs inherit old tags/photosets
- **File date fallback** in `process.py` - Uses file modification time when EXIF is missing
- All admin templates now extend `admin_base.html` for consistent navigation
- Delete operations redirect to appropriate admin pages instead of homepage
- Deployment creates `static/cigarbox` with proper permissions for uploads
- Flask's built-in logger now uses custom logger configuration in both web and API

### Fixed
- Improved directory permissions handling during deployment with better error messages
- Date formatting in photo listings and edit forms
- Tests updated for ImportMeta ForeignKey changes and login requirements

### Migration Required
```bash
# Run after deployment to add CASCADE deletes
docker exec -it -u root cigarbox-web python scripts/migrate_2025_10_25_cascade_deletes.py
```

## [2025-10-25] - Web Upload Interface & Unified Logging

### Added
- **Web Upload Interface** - Modern drag-and-drop upload form at `/upload`
- Multiple file selection (desktop: drag-drop, mobile: camera/gallery)
- Image/video previews with thumbnails
- Real-time upload progress tracking
- Auto-redirect to bulk edit after upload
- Responsive design for mobile and desktop
- **Unified Logging System** - Single log file for all services
- Both web and API containers log to `/app/logs/cigarbox.log`
- Container identification: `[WEB]` and `[API]` prefixes
- Action-based keywords: `UPLOAD_START`, `PHOTO_DB_INSERT`, `S3_UPLOAD`
- One command to monitor everything: `tail -f logs/cigarbox.log`
- Upload link in navigation menu (visible to logged-in users only)

### Changed
- Web uploads now process directly in web.py (no API proxy, no CORS complexity)
- Logger configuration accepts `service_name` parameter for container identification
- Nginx configuration: increased `client_max_body_size` to 16M for web uploads

### Architecture
- Clean separation: web.py = humans with browsers, api.py = CLI tools
- Both use same underlying processing functions (process.py, util.py, aws.py)
- No exposed API keys in browser, no cross-origin calls, session-based auth

### Deployment
Code-only update. Deploy with `fab deploy`.

## [2025-10-25] Open Graph

- Added Open Graph metadata to photos and share pages
- Removed Twitter Cards references (RIP Twitter)
- Validated with https://www.opengraph.xyz/


## [2025-10-24] - Bulk Editor, Admin UI & Photo Processing

### Added
- **Bulk Photo Editor** (`/photos/bulk-edit`) with AJAX saves, smart change tracking, multi-line tag fields with
dropdown autocomplete, date grouping with drill-down, and pagination
- **Admin UI** - Complete admin interface with 10 new templates (dashboard, photos, tags, photosets, users,
shares, create/edit pages)
- **Share Links** - Temporary photo sharing via token (`/share/<token>`) with expiration
- **View Original** button on photo pages (signed S3 URLs, login required)
- **Pagination & search** on all admin list pages (100 per page)
- Tags: search by name
- Photosets: search by title or description
- Users: search by email
- Shares: search by photo ID or token
- **Global lazy loading** (IntersectionObserver with 200px preload)
- **Login/logout redirects** back to current page
- Comprehensive S3 and thumbnail logging (file size, connection status, per-thumbnail success/failure tracking)
- API URL configuration for cli/upload.py (priority: --apiurl arg > CIGARBOX_API_URL env > config.py > localhost)
- Database migration script: ImportMeta cascade delete (scripts/migrate_2025_10_24_importmeta_cascade.py)
- Global exception handler in app.py logs all unhandled errors to stderr

### Changed
- Tag fields now use textarea for better visibility
- Photoset delete redirects to admin photosets page with page preservation
- Cursor auto-positions to end when focusing tag fields
- `/photos/<id>/original` route now requires login and checks permissions
- Thumbnails always output as .jpg regardless of source format (PNG/GIF converted to RGB with white background)
- ImportMeta.photo changed from IntegerField to ForeignKeyField with CASCADE delete
- Foreign key constraints enabled in SQLite (pragmas={'foreign_keys': 1})

### Fixed
- Bulk editor change tracking accumulation across saves
- Bulk tags operation blank success messages
- Lazy loading for logged-out users (script was inside auth check)
- Pagination URL corruption from query param concatenation
- JavaScript button action capture using event listener capture phase
- PNG thumbnails appearing as broken images (templates expected .jpg)
- Orphaned ImportMeta records blocking migration (script now detects and cleans up)
- Bulk edit 500 errors in production (added try/except with full traceback logging)

  ### Migration Required
  ```bash
  # Run after deployment to add cascade delete to ImportMeta
  docker exec -it -u root cigarbox-web python scripts/migrate_2025_10_24_importmeta_cascade.py
  docker-compose restart  # Required to load new db.py ForeignKeyField definition
  ```

## [2025-10-23] - Authentication System

### Added
- Web authentication with Flask-Security-Too (roles: admin/contributor/viewer, permission levels: private/family/friends/public)
- Database fields: User.fs_uniquifier, User.permission_level, Photo.uploaded_by_id, ShareToken model
- Privacy filtering on all routes (NULL treated as public)
- Login UI with 360-day session lifetime
- scripts/ directory for server-side migrations and admin tools

### Changed
- Reorganized: cli/ for client tools (not deployed), scripts/ for server scripts (deployed)
- Updated requirements.txt for Flask-Security-Too (bcrypt <4.0, Flask-WTF, WTForms, email-validator)
- Database connection management with before_request/teardown_request handlers

### Fixed
- SECRET_KEY duplicate definition, UserRoles relationships, Flask-Principal integration disabled

### Migration Required
**Database migration needed!** Run on server after deployment:
```bash
# 1. Run the authentication migration (as root for database write access)
docker exec -it -u root cigarbox-web python scripts/migrate_2025_10_23_add_auth.py

# 2. Create your first admin user (as root)
docker exec -it -u root cigarbox-web python scripts/create_admin.py
```

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
