#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database migration script to add CASCADE delete for Photo relationships

Changes:
- Add CASCADE delete to PhotoTag.photo
- Add CASCADE delete to PhotoPhotoset.photo
- Add CASCADE delete to PhotoPhotoset.photoset
- Add CASCADE delete to ShareToken.photo

This ensures when a Photo (or Photoset) is deleted, all related records are automatically removed,
preventing orphaned relationships and ID reuse issues.

Safe to run multiple times - checks current schema first.
"""

import sys
import os

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from db import *

def migrate():
    """Run the migration"""
    print("Starting CASCADE delete migration for Photo relationships...")

    # Enable foreign keys for this connection
    db.execute_sql("PRAGMA foreign_keys = ON")

    # Check if PhotoTag already has CASCADE (migration already run)
    cursor = db.execute_sql("SELECT sql FROM sqlite_master WHERE type='table' AND name='phototag'")
    result = cursor.fetchone()
    if result and 'ON DELETE CASCADE' in result[0]:
        print("PhotoTag already has CASCADE delete - migration may have been run already")
        print("Checking other tables...")

    # We need to recreate tables since SQLite doesn't support ALTER COLUMN for foreign keys

    # Step 1: PhotoTag
    print("\n1. Migrating PhotoTag...")
    cursor = db.execute_sql("PRAGMA table_info('phototag')")
    columns = {row[1]: row for row in cursor.fetchall()}

    if 'photo' in columns:
        # Check if already has CASCADE
        cursor = db.execute_sql("SELECT sql FROM sqlite_master WHERE type='table' AND name='phototag'")
        table_sql = cursor.fetchone()[0]

        if 'ON DELETE CASCADE' not in table_sql or table_sql.count('ON DELETE CASCADE') < 1:
            print("  Adding CASCADE delete to PhotoTag...")

            # Check for orphaned records first
            cursor = db.execute_sql("""
                SELECT COUNT(*) FROM phototag
                WHERE photo_id NOT IN (SELECT id FROM photo)
                OR tag_id NOT IN (SELECT id FROM tag)
            """)
            orphaned_count = cursor.fetchone()[0]

            if orphaned_count > 0:
                print(f"  Found {orphaned_count} orphaned PhotoTag records. Cleaning up...")
                db.execute_sql("""
                    DELETE FROM phototag
                    WHERE photo_id NOT IN (SELECT id FROM photo)
                    OR tag_id NOT IN (SELECT id FROM tag)
                """)
                print(f"  Deleted {orphaned_count} orphaned records")

            # Rename old table
            db.execute_sql("ALTER TABLE phototag RENAME TO phototag_old")

            # Create new table with CASCADE
            db.execute_sql("""
                CREATE TABLE phototag (
                    id INTEGER PRIMARY KEY,
                    photo_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    ts DATETIME NOT NULL,
                    FOREIGN KEY (photo_id) REFERENCES photo(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tag(id)
                )
            """)

            # Copy data
            db.execute_sql("""
                INSERT INTO phototag (id, photo_id, tag_id, ts)
                SELECT id, photo_id, tag_id, ts FROM phototag_old
            """)

            # Drop old table
            db.execute_sql("DROP TABLE phototag_old")
            print("  ✓ PhotoTag migrated")
        else:
            print("  ✓ PhotoTag already has CASCADE delete")

    # Step 2: PhotoPhotoset
    print("\n2. Migrating PhotoPhotoset...")
    cursor = db.execute_sql("SELECT sql FROM sqlite_master WHERE type='table' AND name='photophotoset'")
    table_sql = cursor.fetchone()[0]

    if 'ON DELETE CASCADE' not in table_sql or table_sql.count('ON DELETE CASCADE') < 2:
        print("  Adding CASCADE delete to PhotoPhotoset...")

        # Check for orphaned records first
        cursor = db.execute_sql("""
            SELECT COUNT(*) FROM photophotoset
            WHERE photo_id NOT IN (SELECT id FROM photo)
            OR photoset_id NOT IN (SELECT id FROM photoset)
        """)
        orphaned_count = cursor.fetchone()[0]

        if orphaned_count > 0:
            print(f"  Found {orphaned_count} orphaned PhotoPhotoset records. Cleaning up...")
            db.execute_sql("""
                DELETE FROM photophotoset
                WHERE photo_id NOT IN (SELECT id FROM photo)
                OR photoset_id NOT IN (SELECT id FROM photoset)
            """)
            print(f"  Deleted {orphaned_count} orphaned records")

        db.execute_sql("ALTER TABLE photophotoset RENAME TO photophotoset_old")

        db.execute_sql("""
            CREATE TABLE photophotoset (
                id INTEGER PRIMARY KEY,
                photo_id INTEGER NOT NULL,
                photoset_id INTEGER NOT NULL,
                ts DATETIME NOT NULL,
                FOREIGN KEY (photo_id) REFERENCES photo(id) ON DELETE CASCADE,
                FOREIGN KEY (photoset_id) REFERENCES photoset(id) ON DELETE CASCADE
            )
        """)

        db.execute_sql("""
            INSERT INTO photophotoset (id, photo_id, photoset_id, ts)
            SELECT id, photo_id, photoset_id, ts FROM photophotoset_old
        """)

        db.execute_sql("DROP TABLE photophotoset_old")
        print("  ✓ PhotoPhotoset migrated")
    else:
        print("  ✓ PhotoPhotoset already has CASCADE delete")

    # Step 3: ShareToken
    print("\n3. Migrating ShareToken...")
    cursor = db.execute_sql("SELECT sql FROM sqlite_master WHERE type='table' AND name='sharetoken'")
    result = cursor.fetchone()

    if result:
        table_sql = result[0]

        if 'ON DELETE CASCADE' not in table_sql:
            print("  Adding CASCADE delete to ShareToken...")

            db.execute_sql("ALTER TABLE sharetoken RENAME TO sharetoken_old")

            db.execute_sql("""
                CREATE TABLE sharetoken (
                    id INTEGER PRIMARY KEY,
                    token VARCHAR(255) UNIQUE NOT NULL,
                    photo_id INTEGER NOT NULL,
                    created_by_id INTEGER,
                    created_at DATETIME NOT NULL,
                    expires_at DATETIME,
                    views INTEGER DEFAULT 0,
                    FOREIGN KEY (photo_id) REFERENCES photo(id) ON DELETE CASCADE
                )
            """)

            db.execute_sql("""
                INSERT INTO sharetoken (id, token, photo_id, created_by_id, created_at, expires_at, views)
                SELECT id, token, photo_id, created_by_id, created_at, expires_at, views FROM sharetoken_old
            """)

            db.execute_sql("DROP TABLE sharetoken_old")
            print("  ✓ ShareToken migrated")
        else:
            print("  ✓ ShareToken already has CASCADE delete")
    else:
        print("  ⓘ ShareToken table doesn't exist yet (will be created with CASCADE)")

    print("\nMigration complete!")
    print("All Photo relationships now have CASCADE delete")

if __name__ == '__main__':
    try:
        migrate()
    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
