#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Reprocess Photos - Generate specific thumbnail sizes for existing photos

Generates missing thumbnail sizes for photos that already exist in the database.
Useful for:
- Adding new thumbnail sizes (_k) to existing photos
- Regenerating corrupted thumbnails with improved scaling (min-dimension)
- Migrating to new thumbnail quality settings

Usage:
  # Dry run to see what would happen
  python scripts/reprocess_thumbnails.py --source b --all --dry-run

  # Test on small batch
  python scripts/reprocess_thumbnails.py --source b --ids 1-100 --force

  # Full reprocess with cleanup (minimal disk space)
  python scripts/reprocess_thumbnails.py --source b --all --force --cleanup --workers 4

  # High quality from originals (slow, large downloads)
  python scripts/reprocess_thumbnails.py --source original --all --force --quality 95
"""

import sys
import os
import argparse
import time
import shutil
import requests
import logging
import datetime
from multiprocessing import Pool, cpu_count

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from db import *
import util
import aws

# Setup logging
def setup_logging():
    """Setup file and console logging"""
    # Create logs directory if it doesn't exist
    log_dir = 'logs' if not os.path.exists('/app') else '/app/logs'
    os.makedirs(log_dir, exist_ok=True)

    # Log filename with timestamp
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'reprocess_thumbnails_{timestamp}.log')

    # Create logger
    logger = logging.getLogger('reprocess')
    logger.setLevel(logging.INFO)

    # File handler (detailed)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler (less verbose)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger, log_file

def parse_ids(ids_string):
    """Parse comma-separated IDs and ranges (e.g., '1,5,10-20')"""
    result = []
    for part in ids_string.split(','):
        if '-' in part:
            start, end = map(int, part.split('-'))
            result.extend(range(start, end + 1))
        else:
            result.append(int(part))
    return result

def get_photo_selection(args):
    """Return Photo queryset based on CLI args"""
    if args.all:
        return Photo.select()
    elif args.ids:
        id_list = parse_ids(args.ids)
        return Photo.select().where(Photo.id.in_(id_list))
    else:
        return Photo.select().limit(0)  # Empty

def parse_sizes(sizes_string):
    """Parse comma-separated thumbnail sizes"""
    return [s.strip() for s in sizes_string.split(',')]

def get_acl_for_size(size):
    """Determine S3 ACL policy for thumbnail size"""
    # Large sizes (_b, _c, _k) are private for AI protection
    # Small sizes (_n, _m, _t) are public for gallery performance
    # _k (500px) kept private as it's valuable for AI training
    if size in ['b', 'c', 'k']:
        return 'private'
    else:
        return 'public-read'

def download_from_s3(s3_key, local_path, config, is_private=False, logger=None):
    """
    Download file from S3 to local cache

    Args:
        s3_key: S3 object key (path in bucket)
        local_path: Where to save the file locally
        config: App config dict
        is_private: Whether to use signed URL (for private objects)
        logger: Logger instance

    Returns:
        True on success, False on failure
    """
    try:
        # Get URL (signed for private, direct for public)
        if is_private:
            url = aws.getPrivateURL(config, s3_key, expiry=3600)
            if not url:
                if logger:
                    logger.error(f'Failed to get signed URL for {s3_key}')
                return False
        else:
            bucket = config['S3_BUCKET_NAME']
            url = f"http://s3.amazonaws.com/{bucket}/{s3_key}"

        # Download file
        if logger:
            logger.info(f'Downloading {s3_key} from S3...')
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()

        # Create directories if needed
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        # Save to local cache
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        file_size = os.path.getsize(local_path)
        if logger:
            logger.info(f'Downloaded {s3_key} ({file_size/1024:.1f} KB)')

        return True

    except Exception as e:
        if logger:
            logger.error(f'Download failed for {s3_key}: {e}')
        print(f'  Download failed: {e}')
        return False

def get_source_file(photo, source_type, config, print_progress=True, logger=None):
    """
    Get source file path, downloading from S3 if needed

    Args:
        photo: Photo database object
        source_type: 'original', 't', 'm', 'n', 'k', 'c', or 'b'
        config: App config dict
        print_progress: Print progress indicators (D for download)
        logger: Logger instance

    Returns:
        (source_path, downloaded_flag) or (None, False) on error
    """
    (sha1Path, filename) = util.getSha1Path(photo.sha1)
    local_archive = config['LOCALARCHIVEPATH']

    # Determine source file path and S3 key
    if source_type == 'original':
        local_path = f'{local_archive}/{sha1Path}/{filename}.{photo.filetype}'
        s3_key = f'{sha1Path}/{filename}.{photo.filetype}'
        is_private = True  # Originals always private
    else:
        local_path = f'{local_archive}/{sha1Path}/{filename}_{source_type}.jpg'
        s3_key = f'{sha1Path}/{filename}_{source_type}.jpg'
        is_private = (source_type in ['b', 'c'])  # Large thumbnails private

    # Check if exists locally
    if os.path.exists(local_path):
        if logger:
            logger.debug(f'Photo {photo.id}: Using cached _{source_type}')
        return (local_path, False)

    # Download from S3
    if print_progress:
        print('D', end='', flush=True)

    if download_from_s3(s3_key, local_path, config, is_private, logger):
        return (local_path, True)
    else:
        return (None, False)

def process_photo(photo_id, sizes, config, source_type='original', quality=95,
                  dry_run=False, force=False, cleanup=False, print_progress=True, logger=None):
    """
    Process a single photo - generate specified thumbnail sizes

    Args:
        photo_id: Photo database ID
        sizes: List of thumbnail size codes (e.g., ['k', 'c'])
        config: App config dict
        source_type: Source for generation ('original', 'b', 'c', etc.)
        quality: JPEG quality (1-100)
        dry_run: If True, don't actually generate/upload
        force: If True, regenerate even if exists
        cleanup: If True, delete downloaded files after processing
        print_progress: Print progress indicators (D/G/U)
        logger: Logger instance

    Returns:
        (success, generated_count, skipped_count, error_message, downloaded_files)
    """
    downloaded_files = []

    try:
        photo = Photo.get_by_id(photo_id)
        (sha1Path, filename) = util.getSha1Path(photo.sha1)

        if logger:
            logger.info(f'Processing photo {photo_id}: {sha1Path}/{filename}')

        local_archive = config['LOCALARCHIVEPATH']

        # Get source file (may download from S3)
        source_path, was_downloaded = get_source_file(photo, source_type, config, print_progress, logger)

        if not source_path:
            return (False, 0, 0, f'Source file not found: _{source_type}', [])

        if was_downloaded:
            downloaded_files.append(source_path)

        generated = 0
        skipped = 0
        generated_files = []

        # If using a thumbnail as source, create temp copy with base filename
        # so genThumbnail creates correct output names
        temp_copy_path = None
        if source_type != 'original':
            source_relative = os.path.relpath(source_path, local_archive)
            base_filename = source_relative.rsplit('_', 1)[0] + '.jpg'
            base_full_path = os.path.join(local_archive, base_filename)
            shutil.copy2(source_path, base_full_path)
            temp_copy_path = base_full_path
            source_for_thumbnails = base_filename
        else:
            source_for_thumbnails = os.path.relpath(source_path, local_archive)

        for size in sizes:
            thumb_filename = f'{sha1Path}/{filename}_{size}.jpg'
            thumb_local_path = f'{local_archive}/{thumb_filename}'

            # Skip if already exists (unless force)
            if os.path.exists(thumb_local_path) and not force:
                skipped += 1
                continue

            if dry_run:
                generated += 1
                continue

            # Generate thumbnail
            try:
                if print_progress:
                    print('G', end='', flush=True)

                if logger:
                    logger.info(f'Photo {photo_id}: Generating _{size}.jpg')

                thumb_result = util.genThumbnail(
                    filename=source_for_thumbnails,
                    thumbnailType=size,
                    config=config,
                    regen=force
                )

                generated_files.append(thumb_local_path)

                # Upload to S3 with appropriate ACL
                if print_progress:
                    print('U', end='', flush=True)

                acl = get_acl_for_size(size)

                if logger:
                    logger.info(f'Photo {photo_id}: Uploading _{size}.jpg (ACL: {acl})')

                upload_success = aws.uploadToS3(
                    thumb_local_path,
                    thumb_filename,
                    config,
                    regen=True,
                    policy=acl
                )

                if upload_success:
                    generated += 1
                    if logger:
                        logger.info(f'Photo {photo_id}: Successfully uploaded _{size}.jpg')

                        # Log URL for _k size for spot checking
                        if size == 'k':
                            bucket = config['S3_BUCKET_NAME']
                            s3_url = f"http://s3.amazonaws.com/{bucket}/{thumb_filename}"
                            logger.info(f'Photo {photo_id}: _k URL for spot check: {s3_url}')
                else:
                    if logger:
                        logger.error(f'Photo {photo_id}: S3 upload failed for _{size}.jpg')
                    return (False, generated, skipped, f'S3 upload failed for {thumb_filename}', downloaded_files)

            except Exception as e:
                # Clean up temp copy before returning error
                if temp_copy_path and os.path.exists(temp_copy_path):
                    os.remove(temp_copy_path)
                if logger:
                    logger.error(f'Photo {photo_id}: Thumbnail generation failed - {str(e)}')
                return (False, generated, skipped, f'Thumbnail generation failed: {str(e)}', downloaded_files)

        # Clean up temporary copy of source file
        if temp_copy_path and os.path.exists(temp_copy_path):
            os.remove(temp_copy_path)
            if logger:
                logger.debug(f'Photo {photo_id}: Cleaned up temporary source copy')

        if logger:
            logger.info(f'Photo {photo_id}: Complete - generated {generated}, skipped {skipped}')

        # Cleanup if requested
        if cleanup and not dry_run:
            # Delete downloaded source file
            for filepath in downloaded_files:
                try:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                except Exception as e:
                    print(f'  Warning: Could not delete {filepath}: {e}')

            # Delete generated thumbnails (already uploaded to S3)
            for filepath in generated_files:
                try:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                except Exception as e:
                    print(f'  Warning: Could not delete {filepath}: {e}')

        return (True, generated, skipped, None, downloaded_files)

    except Photo.DoesNotExist:
        return (False, 0, 0, f'Photo {photo_id} not found in database', downloaded_files)
    except Exception as e:
        return (False, 0, 0, str(e), downloaded_files)

def process_photo_wrapper(args):
    """Wrapper for multiprocessing Pool.map"""
    return process_photo(*args)

def main():
    # Setup logging first
    logger, log_file = setup_logging()

    parser = argparse.ArgumentParser(
        description='Reprocess photos to generate specific thumbnail sizes',
        epilog='Examples:\n'
               '  python scripts/reprocess_thumbnails.py --source b --all --force --cleanup --workers 4\n'
               '  python scripts/reprocess_thumbnails.py --source original --ids 1-100 --quality 95',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Selection
    selection_group = parser.add_mutually_exclusive_group(required=True)
    selection_group.add_argument('--all', action='store_true',
                                 help='Process all photos')
    selection_group.add_argument('--ids',
                                 help='Comma-separated IDs or ranges (e.g., 1,5,10-20)')

    # Actions
    parser.add_argument('--sizes', default='t,m,n,k,c,b',
                       help='Comma-separated sizes to generate (default: all). Options: t,m,n,k,c,b')
    parser.add_argument('--source', default='original',
                       help='Source for generation: original, t, m, n, k, c, b (default: original)')
    parser.add_argument('--quality', type=int, default=95,
                       help='JPEG quality 1-100 (default: 95)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without actually doing it')
    parser.add_argument('--force', action='store_true',
                       help='Regenerate even if thumbnail already exists')
    parser.add_argument('--cleanup', action='store_true',
                       help='Delete downloaded files after processing (saves disk space)')
    parser.add_argument('--workers', type=int, default=1,
                       help='Number of parallel workers (default: 1)')
    parser.add_argument('--yes', action='store_true',
                       help='Skip confirmation prompt (for non-interactive execution)')

    args = parser.parse_args()

    print('='*60)
    print('Reprocess Thumbnails')
    print('='*60)
    print()
    print(f'Logging to: {log_file}')
    print()

    logger.info('='*60)
    logger.info('Reprocess Thumbnails Script Started')
    logger.info('='*60)
    logger.info(f'Arguments: {vars(args)}')

    # Get photos to process
    photos = get_photo_selection(args)
    total = photos.count()

    if total == 0:
        print('No photos selected!')
        return

    sizes = parse_sizes(args.sizes)

    # Remove source size from generation list (no point regenerating _b from _b)
    if args.source != 'original' and args.source in sizes:
        sizes.remove(args.source)
        print(f'Note: Skipping _{args.source}.jpg generation (same as source)')
        print()

    print(f'Photos to process: {total}')
    print(f'Source: _{args.source}')
    print(f'Sizes to generate: {", ".join([f"_{s}.jpg" for s in sizes])}')
    print(f'JPEG quality: {args.quality}')
    print(f'Total operations: {total * len(sizes)}')
    if args.cleanup:
        print(f'Cleanup: YES (delete files after upload)')
    else:
        print(f'Cleanup: NO (keep files locally)')
    print()

    if args.dry_run:
        print('DRY RUN MODE - No changes will be made')
        print()

    # Show ACL policy per size
    print('ACL Policy per size:')
    for size in sizes:
        acl = get_acl_for_size(size)
        print(f'  _{size}.jpg -> {acl}')
    print()

    # Confirm unless dry-run or --yes flag
    if not args.dry_run and not args.yes:
        confirm = input(f'Process {total} photos? [y/N]: ')
        if confirm.lower() != 'y':
            print('Cancelled')
            return
        print()

    # Progress indicators legend
    if not args.dry_run and args.workers == 1:
        print('Progress indicators:')
        print('  D = Download from S3')
        print('  G = Generate thumbnail')
        print('  U = Upload to S3')
        print('  . = Photo complete (success)')
        print('  x = Photo failed')
        print()
        print('Processing...')
        print()

    # Process photos
    start_time = time.time()
    success_count = 0
    fail_count = 0
    total_generated = 0
    total_skipped = 0
    total_downloaded = 0

    if args.workers > 1:
        # Parallel processing (no detailed progress indicators)
        print(f'Processing with {args.workers} workers...')
        print()

        # Disable progress indicators for parallel mode (they won't work well)
        # Note: logging won't work well with multiprocessing
        pool_args = [(p.id, sizes, app.config, args.source, args.quality, args.dry_run, args.force, args.cleanup, False, None)
                     for p in photos]
        with Pool(processes=args.workers) as pool:
            # Use imap to get results as they complete (not all at once)
            results_iter = pool.imap(process_photo_wrapper, pool_args)

            i = 0
            for success, generated, skipped, error, downloaded in results_iter:
                i += 1
                # Get the photo for logging
                photo = list(photos)[i-1]

                if success:
                    success_count += 1
                    total_generated += generated
                    total_skipped += skipped
                    total_downloaded += len(downloaded)

                    logger.info(f'Photo {photo.id}: Complete - generated {generated}, skipped {skipped}')

                    # Log _k URL for spot checking (construct it since we don't have it from worker)
                    (sha1Path, filename) = util.getSha1Path(photo.sha1)
                    thumb_filename = f'{sha1Path}/{filename}_k.jpg'
                    bucket = app.config['S3_BUCKET_NAME']
                    s3_url = f"http://s3.amazonaws.com/{bucket}/{thumb_filename}"
                    logger.info(f'Photo {photo.id}: _k URL for spot check: {s3_url}')

                    if not args.dry_run:
                        print('.', end='')
                        sys.stdout.flush()  # Force flush for multiprocessing
                else:
                    fail_count += 1
                    logger.error(f'Photo {photo.id}: Failed - {error}')
                    print(f'\n✗ Error: {error}')
                    sys.stdout.flush()

                # Progress update every 100 photos
                if i % 100 == 0:
                    elapsed = time.time() - start_time
                    rate = i / elapsed
                    remaining = (total - i) / rate if rate > 0 else 0
                    percent = (i * 100) // total
                    progress_msg = f'[{i}/{total}] {percent}% complete - {rate:.1f} photos/sec - ETA: {remaining/60:.1f} min'
                    print(f'\n{progress_msg}')
                    sys.stdout.flush()
                    logger.info(progress_msg)

    else:
        # Single-threaded processing
        for i, photo in enumerate(photos, 1):
            success, generated, skipped, error, downloaded = process_photo(
                photo.id, sizes, app.config, args.source, args.quality,
                args.dry_run, args.force, args.cleanup, print_progress=not args.dry_run, logger=logger
            )

            if success:
                success_count += 1
                total_generated += generated
                total_skipped += skipped
                total_downloaded += len(downloaded)
                if not args.dry_run:
                    print('.', end='', flush=True)
            else:
                fail_count += 1
                if not args.dry_run:
                    print('x', end='', flush=True)
                print(f'\n✗ Photo {photo.id}: {error}')

            # Progress update every 100 photos
            if i % 100 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed
                remaining = (total - i) / rate if rate > 0 else 0
                percent = (i * 100) // total
                print(f'\n[{i}/{total}] {percent}% complete - {rate:.1f} photos/sec - ETA: {remaining/60:.1f} min', end='\n' if not args.dry_run else '')

    print()  # Newline after dots
    elapsed = time.time() - start_time

    print()
    print('='*60)
    if args.dry_run:
        print('DRY RUN COMPLETE')
        print(f'Would have generated: {total_generated} thumbnails')
        print(f'Would have skipped: {total_skipped} (already exist)')
        logger.info('DRY RUN COMPLETE')
        logger.info(f'Would have generated: {total_generated} thumbnails')
    else:
        print('PROCESSING COMPLETE')
        print(f'Success: {success_count} photos')
        print(f'Failed: {fail_count} photos')
        print(f'Generated: {total_generated} thumbnails')
        print(f'Skipped: {total_skipped} (already exist)')
        print(f'Downloaded: {total_downloaded} files from S3')
        print(f'Time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)')
        if success_count > 0:
            print(f'Rate: {success_count/elapsed:.1f} photos/sec')

        logger.info('='*60)
        logger.info('PROCESSING COMPLETE')
        logger.info(f'Success: {success_count} photos')
        logger.info(f'Failed: {fail_count} photos')
        logger.info(f'Generated: {total_generated} thumbnails')
        logger.info(f'Skipped: {total_skipped} (already exist)')
        logger.info(f'Downloaded: {total_downloaded} files from S3')
        logger.info(f'Time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)')
        if success_count > 0:
            logger.info(f'Rate: {success_count/elapsed:.1f} photos/sec')
        logger.info('='*60)
    print('='*60)
    print(f'Log file: {log_file}')

if __name__ == '__main__':
    main()
