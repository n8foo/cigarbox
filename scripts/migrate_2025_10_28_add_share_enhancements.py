#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database migration script to add share enhancements

Changes to ShareToken table:
- Add share_type VARCHAR (default 'photo')
- Make photo_id nullable
- Add photoset_id (nullable FK to Photoset)
- Add comment TEXT (nullable)
- Add allow_download BOOLEAN (default False)
- Add max_views INTEGER (nullable, NULL = unlimited)

This enables unified sharing for both photos and photosets with enhanced features:
- Comments/metadata on shares
- Download original option
- View limits
- Future extensibility for other share types

Safe to run multiple times - checks if columns already exist.
"""

import sys
import os

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from db import *

def migrate():
    """Run the migration"""
    print("Starting ShareToken enhancements migration...")

    # Enable foreign keys for this connection
    db.execute_sql("PRAGMA foreign_keys = ON")

    # Check current ShareToken schema
    cursor = db.execute_sql("SELECT sql FROM sqlite_master WHERE type='table' AND name='sharetoken'")
    result = cursor.fetchone()

    if not result:
        print("ERROR: ShareToken table doesn't exist!")
        sys.exit(1)

    table_sql = result[0]
    print(f"\nCurrent ShareToken schema:\n{table_sql}\n")

    # Check if migration already run
    cursor = db.execute_sql("PRAGMA table_info('sharetoken')")
    columns = {row[1]: row for row in cursor.fetchall()}

    if 'share_type' in columns:
        print("✓ share_type column already exists - migration may have been run already")
        return

    print("Adding new columns to ShareToken...")

    # SQLite doesn't support ALTER COLUMN, so we need to recreate the table
    # 1. Rename old table
    db.execute_sql("ALTER TABLE sharetoken RENAME TO sharetoken_old")
    print("  Renamed sharetoken to sharetoken_old")

    # 2. Create new table with all enhancements
    db.execute_sql("""
        CREATE TABLE sharetoken (
            id INTEGER PRIMARY KEY,
            token VARCHAR(255) UNIQUE NOT NULL,
            share_type VARCHAR(20) DEFAULT 'photo' NOT NULL,
            photo_id INTEGER,
            photoset_id INTEGER,
            comment TEXT,
            allow_download BOOLEAN DEFAULT 0 NOT NULL,
            max_views INTEGER,
            created_by_id INTEGER,
            created_at DATETIME NOT NULL,
            expires_at DATETIME,
            views INTEGER DEFAULT 0 NOT NULL,
            FOREIGN KEY (photo_id) REFERENCES photo(id) ON DELETE CASCADE,
            FOREIGN KEY (photoset_id) REFERENCES photoset(id) ON DELETE CASCADE
        )
    """)
    print("  Created new sharetoken table with enhancements")

    # 3. Copy existing data (set share_type='photo' for all existing records)
    db.execute_sql("""
        INSERT INTO sharetoken
            (id, token, share_type, photo_id, photoset_id, comment, allow_download,
             max_views, created_by_id, created_at, expires_at, views)
        SELECT
            id, token, 'photo', photo_id, NULL, NULL, 0,
            NULL, created_by_id, created_at, expires_at, views
        FROM sharetoken_old
    """)

    # Count migrated records
    cursor = db.execute_sql("SELECT COUNT(*) FROM sharetoken")
    count = cursor.fetchone()[0]
    print(f"  Migrated {count} existing share tokens")

    # 4. Drop old table
    db.execute_sql("DROP TABLE sharetoken_old")
    print("  Dropped sharetoken_old")

    print("\nMigration complete!")
    print("ShareToken now supports:")
    print("  - Unified photo and photoset sharing (share_type)")
    print("  - Comments/metadata (comment)")
    print("  - Download originals (allow_download)")
    print("  - View limits (max_views)")

if __name__ == '__main__':
    try:
        migrate()
    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
