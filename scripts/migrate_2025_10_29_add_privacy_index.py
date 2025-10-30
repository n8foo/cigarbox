#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database migration script to add index on photo.privacy column

Performance optimization for navigation and filtering queries.

Changes:
- Add index idx_photo_privacy on photo(privacy)

This dramatically speeds up queries that filter by privacy level:
- Photostream navigation (42K photos: 4.67ms → <1ms)
- Photoset/tag/date filtered views
- Any privacy-based queries

Safe to run multiple times - checks if index already exists.
"""

import sys
import os

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from db import *

def migrate():
    """Run the migration"""
    print("Starting privacy index migration...")

    # Check if index already exists
    cursor = db.execute_sql("""
        SELECT name FROM sqlite_master
        WHERE type='index' AND name='idx_photo_privacy'
    """)
    existing = cursor.fetchone()

    if existing:
        print("✓ Index idx_photo_privacy already exists, skipping")
        return

    # Create the index
    print("Creating index idx_photo_privacy on photo(privacy)...")
    db.execute_sql("CREATE INDEX idx_photo_privacy ON photo(privacy)")

    print("✓ Index created successfully")

    # Analyze query performance improvement
    print("\nVerifying index...")
    cursor = db.execute_sql("""
        EXPLAIN QUERY PLAN
        SELECT * FROM photo
        WHERE privacy = 2 AND id < 20000
        ORDER BY id DESC
        LIMIT 1
    """)
    plan = cursor.fetchall()
    print("Query plan:")
    for row in plan:
        print(f"  {row}")

    # Show index stats
    cursor = db.execute_sql("""
        SELECT name, sql FROM sqlite_master
        WHERE type='index' AND tbl_name='photo'
    """)
    indexes = cursor.fetchall()
    print(f"\nTotal indexes on photo table: {len(indexes)}")
    for name, sql in indexes:
        if sql:  # Skip auto-created indexes
            print(f"  • {name}")

    print("\n✓ Migration complete!")
    print("\nExpected performance improvement:")
    print("  Photostream navigation: 4-5ms → <1ms")
    print("  All privacy-filtered queries will benefit")

def main():
    """Main entry point"""
    print("="*60)
    print("Migration: Add privacy index for navigation performance")
    print("="*60)
    print()

    try:
        migrate()
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
