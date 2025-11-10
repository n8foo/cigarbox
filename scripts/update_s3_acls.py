#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Update S3 ACLs for existing photos - Fast boto3 approach

Changes ACL permissions on existing S3 objects without re-uploading.
Much faster than regenerating and re-uploading thumbnails.

Usage:
  python scripts/update_s3_acls.py --all                    # All photos
  python scripts/update_s3_acls.py --ids 1,2,3,100-200     # Specific IDs
  python scripts/update_s3_acls.py --dry-run --all         # Preview only
  python scripts/update_s3_acls.py --sizes b,c --all       # Only _b and _c
"""

import sys
import os
import argparse
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from db import *
import aws
import util

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
        print("Error: Must specify --all or --ids")
        sys.exit(1)

def get_sizes_to_update(args):
    """Parse which sizes to update"""
    if args.sizes:
        return args.sizes.split(',')
    # Default: update _b and _c (AI training protection)
    return ['b', 'c']

def get_policy_for_size(size):
    """Determine ACL policy for a given size"""
    # Make large sizes private (AI training protection)
    if size in ['b', 'c']:
        return 'private'
    else:
        return 'public-read'

def update_s3_acl(s3_key, policy, config, dry_run=False):
    """
    Update ACL for an S3 object without re-uploading

    Returns: (success, error_message)
    """
    if dry_run:
        print(f"  [DRY RUN] Would set {s3_key} -> {policy}")
        return True, None

    try:
        s3 = aws.get_s3_client(config)
        bucket_name = config['S3_BUCKET_NAME']

        # Update the object's ACL
        s3.put_object_acl(
            Bucket=bucket_name,
            Key=s3_key,
            ACL=policy
        )
        return True, None

    except Exception as e:
        return False, str(e)

def main():
    parser = argparse.ArgumentParser(
        description='Update S3 ACLs for existing photos (fast, no re-upload)'
    )

    # Selection
    parser.add_argument('--all', action='store_true',
                       help='Update all photos')
    parser.add_argument('--ids',
                       help='Comma-separated IDs or ranges (e.g., 1,5,10-20)')

    # Options
    parser.add_argument('--sizes', default='b,c',
                       help='Sizes to update (default: b,c for AI protection)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')
    parser.add_argument('--force', action='store_true',
                       help='Skip confirmation prompt')

    args = parser.parse_args()

    print("="*60)
    print("S3 ACL Update Script - boto3 Fast Approach")
    print("="*60)
    print()

    # Get photos to process
    photos = get_photo_selection(args)
    total = photos.count()

    # Get sizes to update
    sizes = get_sizes_to_update(args)

    print(f"Photos to process: {total}")
    print(f"Sizes to update: {', '.join(['_' + s + '.jpg' for s in sizes])}")
    print(f"Total S3 operations: {total * len(sizes)}")
    print()

    if args.dry_run:
        print("DRY RUN MODE - No changes will be made")
        print()

    # Show policy for each size
    print("ACL Policy per size:")
    for size in sizes:
        policy = get_policy_for_size(size)
        print(f"  _{size}.jpg -> {policy}")
    print()

    # Confirm
    if not args.force and not args.dry_run:
        confirm = input(f'Update ACLs for {total} photos? [y/N]: ')
        if confirm.lower() != 'y':
            print('Cancelled')
            return

    # Process photos
    success_count = 0
    fail_count = 0
    start_time = time.time()

    for i, photo in enumerate(photos, 1):
        photo_success = True

        # Compute URI from SHA1 (same as web.py does)
        (sha1Path, filename) = util.getSha1Path(photo.sha1)
        photo_uri = f'{sha1Path}/{filename}'

        for size in sizes:
            # Build S3 key
            s3_key = f'{photo_uri}_{size}.jpg'
            policy = get_policy_for_size(size)

            # Update ACL
            success, error = update_s3_acl(s3_key, policy, app.config, args.dry_run)

            if success:
                if not args.dry_run:
                    #print(f"  ✓ Updated {s3_key} -> {policy}")
                    print(f".", end="")
            else:
                photo_success = False
                print(f"  ✗ Failed {s3_key}: {error}")

        if photo_success:
            success_count += 1
        else:
            fail_count += 1

        # Progress every 10 photos
        if i % 10 == 0:
            elapsed = time.time() - start_time
            rate = i / elapsed
            remaining = (total - i) / rate if rate > 0 else 0
            print(f"Progress: {i}/{total} ({i*100//total}%) - "
                  f"{rate:.1f} photos/sec - "
                  f"ETA: {remaining/60:.1f} min")

    # Summary
    elapsed = time.time() - start_time
    print()
    print("="*60)
    if args.dry_run:
        print(f"DRY RUN COMPLETE - No changes made")
        print(f"Would have processed: {total} photos, {total * len(sizes)} ACL updates")
    else:
        print(f"UPDATE COMPLETE")
        print(f"Success: {success_count} photos")
        print(f"Failed: {fail_count} photos")
        print(f"Time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        print(f"Rate: {total/elapsed:.1f} photos/second")
    print("="*60)

if __name__ == '__main__':
    main()
