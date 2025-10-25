# CigarBox Testing Guide

## Overview

This document provides testing procedures for CigarBox features, focusing on manual testing of UI-heavy features and automated testing where appropriate.

## Automated Tests

### Test Files
- `tests/test_db.py` - Database model tests
- `tests/test_util.py` - Utility function tests
- `tests/test_process.py` - Photo processing function tests
- `tests/test_aws.py` - AWS S3 integration tests
- `tests/test_web.py` - Web route tests
- `tests/test_api.py` - API endpoint tests
- `tests/test_integration_upload.py` - End-to-end upload workflow

### Running Tests

Run all tests locally:
```bash
python run_tests.py              # All unit tests (discovers from tests/)
python -m pytest tests/          # Alternative with pytest
```

Run tests against test server:
```bash
fab test                         # Tests against remote server (reads fabric.yaml)
fab test-remote --role=test      # Tests inside Docker container
```

Run specific test:
```bash
python -m unittest tests.test_db.TestDatabaseModels.test_photo_creation
```

Current coverage: **59 unit tests + 6 integration tests = 65 total**

## Manual Testing Checklist

### Pre-Deployment Testing
Before deploying to production, test these features on the test server.

#### 🎨 Bulk Photo Editor
Navigate to `/photos/bulk-edit?ids=1,2,3` or click "Bulk Edit" from a tag page

- [ ] Page loads showing photos with tag/privacy fields
- [ ] Tag autocomplete - Type first few letters, dropdown appears
- [ ] Space accepts autocomplete, adds comma
- [ ] Edit a tag, hit Enter - green success alert appears
- [ ] Refresh page - change persists
- [ ] Only changed photos are saved (check console log count)
- [ ] Tag fields wrap long lists (textarea, not input)
- [ ] Cursor jumps to end when focused
- [ ] Tab moves between fields (not autocomplete)
- [ ] Bulk "Add Tags" / "Apply Privacy" / "Add to Photoset" work
- [ ] Date grouping headers appear
- [ ] "Just this group" links filter correctly
- [ ] Pagination works without URL corruption

#### 🔐 Authentication & Permissions

- [ ] **Anonymous**: View photoset, images lazy load, no "View Original" button
- [ ] **Login**: From photoset page, returns to photoset after login
- [ ] **Logout**: Returns to same page after logout
- [ ] **View Original**: Button appears when logged in, opens in new tab
- [ ] **Signed URL**: Original image loads via temporary S3 URL
- [ ] **Permission check**: Can't access others' private photos

#### 👨‍💼 Admin Features

- [ ] `/admin/photosets` - Shows count in heading "All Photosets (X)"
- [ ] Pagination appears if > 100 photosets
- [ ] Delete photoset → redirects to admin photosets (not photostream)
- [ ] Returns to same page number after delete
- [ ] `/admin/photos` - Images lazy load
- [ ] `/admin/tags` - Tag operations work

#### 🖼️ Image Display & Lazy Loading

- [ ] Photostream - images lazy load as you scroll
- [ ] Photosets page - thumbnail grids lazy load
- [ ] Photoset detail - individual photos lazy load
- [ ] Tag page - tagged photos lazy load
- [ ] **Logged out** - all lazy loading still works

## Bugs Fixed

### Critical Race Condition (db.py)
**Issue**: All model `ts` fields used `datetime.datetime.now` without parentheses, causing the same timestamp object to be reused for all records.

**Fix**: Changed to `lambda: datetime.datetime.now()` to ensure each record gets a unique timestamp.

**Files affected**: db.py (lines 23, 28, 33, 38, 42, 47, 52, 57, 66, 78)

### Database Query Bugs (process.py)

1. **Missing Photo. prefix** (line 71)
   - Issue: `where(id == photo_id)` should be `where(Photo.id == photo_id)`

2. **Missing Photo. prefix** (line 94)
   - Issue: Same as above in replacePhoto function

3. **Wrong logger format** (line 108)
   - Issue: Used tuple instead of multiple arguments
   - Fix: Changed to proper format string syntax

4. **Undefined variable** (line 114)
   - Issue: Returned `id` instead of `phototag.id`
   - Fix: Return `phototag.id` and added return in DoesNotExist case

5. **Undefined response variable** (lines 128, 138)
   - Issue: Referenced undefined `response` dict
   - Fix: Removed response references, use logger and return tuple

### Logic Errors (web.py)

1. **Duplicate function name** (line 41)
   - Issue: 500 error handler named `page_not_found` (same as 404)
   - Fix: Renamed to `internal_server_error`

2. **Wrong template** (line 42)
   - Issue: 500 errors rendered 404.html
   - Fix: Changed to render 500.html

3. **Tuple instead of string** (line 162)
   - Issue: `thumb.uri = '%s/%s_t.jpg' % (getSha1Path(thumb.sha1))`
   - Fix: Unpack tuple: `(sha1Path, filename) = getSha1Path(...)`

4. **Missing @login_required** (lines 135, 182)
   - Issue: Delete functions had decorator commented out
   - Fix: Re-enabled @login_required decorator

### AWS Bug (aws.py)

**Variable name case mismatch** (line 43)
- Issue: `k.key.delete(S3key)` but variable is `S3Key`
- Fix: Changed to `k.delete()` (correct boto API usage)

### API Bugs (api.py)

1. **Missing validation** (line 94)
   - Issue: `clientfilename = request.form['clientfilename']` crashes if missing
   - Fix: Changed to `request.form.get('clientfilename', None)`

2. **Wrong variable initialization** (lines 148, 177)
   - Issue: `tags=list` assigns the type, not an empty list
   - Fix: Changed to `tags = []`

3. **Unreachable code** (line 251)
   - Issue: Logger after return statement
   - Fix: Moved logger before return

4. **Debug mode in production** (line 253)
   - Issue: `app.config['DEBUG'] = True`
   - Fix: Changed to `False`

### Utility Bug (util.py)

**Missing GPS bounds checking** (lines 119-144)
- Issue: No validation of GPS data structure, can crash on malformed data
- Fix: Added try/except with bounds checking for GPS fields

## Test Coverage

### Database Tests (test_db.py)
- Photo creation and uniqueness constraints
- Timestamp race condition verification
- Tag, Photoset, and Gallery creation
- Foreign key relationships
- Import metadata tracking
- User and role creation

### Utility Tests (test_util.py)
- String normalization
- SHA1 path generation
- File hashing
- Base58 encoding/decoding
- Thumbnail generation
- EXIF extraction
- GPS data error handling

### Process Tests (test_process.py)
- File type extraction
- Photo database operations
- Photoset creation and management
- Tag operations (add/remove)
- Tag normalization
- Photo-tag relationships
- S3 import status tracking
- Privacy settings

### AWS Tests (test_aws.py)
- S3 upload operations
- S3 deletion
- Private URL generation
- Bucket creation
- Error handling

### Web Tests (test_web.py)
- Route accessibility
- Error handlers (404, 500)
- File upload validation
- Pagination
- Photo viewing
- Tag listing

### API Tests (test_api.py)
- SHA1 lookup
- Tag operations via API
- Photoset operations
- File upload with metadata
- Input validation
- Error responses

## Dependencies for Testing

The tests require the following Python packages:
- unittest (built-in)
- peewee
- PIL/Pillow
- flask
- boto (for AWS mocking)

## Notes

- Tests use temporary SQLite databases that are cleaned up after each test
- AWS tests use mocking to avoid actual S3 calls
- File upload tests use temporary directories
- All tests are isolated and can run in any order
