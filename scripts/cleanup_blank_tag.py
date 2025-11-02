#!/usr/bin/env python
"""
Cleanup script to remove blank tag from database.

This script removes the blank tag (empty string) and all its photo associations.
Run this from the project root directory:
  python scripts/cleanup_blank_tag.py
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import db, Tag, PhotoTag

def cleanup_blank_tag():
    """Remove blank tag and its associations"""
    # Find blank tags
    blank_tags = Tag.select().where((Tag.name == '') | (Tag.name.is_null()))

    count = 0
    for tag in blank_tags:
        print(f"Found blank tag: id={tag.id}, name='{tag.name}'")

        # Count associated photos
        photo_count = PhotoTag.select().where(PhotoTag.tag == tag).count()
        print(f"  - {photo_count} photo associations")

        # Delete associations
        deleted = PhotoTag.delete().where(PhotoTag.tag == tag).execute()
        print(f"  - Deleted {deleted} PhotoTag records")

        # Delete tag
        tag.delete_instance()
        print(f"  - Deleted tag")
        count += 1

    if count == 0:
        print("No blank tags found!")
    else:
        print(f"\nCleaned up {count} blank tag(s)")

if __name__ == '__main__':
    print("Blank Tag Cleanup Script")
    print("=" * 50)

    # Confirm before running
    response = input("\nThis will delete blank tags and their associations. Continue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Aborted.")
        sys.exit(0)

    cleanup_blank_tag()
    print("\nDone!")
