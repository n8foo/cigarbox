#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database migration script to add cascade delete for ImportMeta

Changes:
- Convert ImportMeta.photo from IntegerField to ForeignKeyField with CASCADE delete
- This ensures ImportMeta records are automatically deleted when their parent Photo is deleted

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
    print("Starting ImportMeta cascade delete migration...")

    # Enable foreign keys for this connection
    db.execute_sql("PRAGMA foreign_keys = ON")

    # SQLite doesn't support modifying foreign key constraints directly
    # We need to recreate the table with the new schema

    # Step 1: Check if we need to migrate
    # Check if photo_id column exists (new schema) vs photo column (old schema)
    cursor = db.execute_sql("PRAGMA table_info('importmeta')")
    columns = {row[1]: row for row in cursor.fetchall()}  # row[1] is column name

    if 'photo_id' in columns:
        print("ImportMeta already migrated (has photo_id column) - skipping")
        return

    if 'photo' not in columns:
        print("ERROR: ImportMeta table has unexpected schema")
        return

    print("Creating new ImportMeta table with CASCADE delete...")

    # Step 2: Check for orphaned records
    print("Checking for orphaned ImportMeta records...")
    cursor = db.execute_sql("""
        SELECT COUNT(*) FROM importmeta
        WHERE photo NOT IN (SELECT id FROM photo)
    """)
    orphaned_count = cursor.fetchone()[0]

    if orphaned_count > 0:
        print(f"Found {orphaned_count} orphaned ImportMeta records. Cleaning up...")
        db.execute_sql("""
            DELETE FROM importmeta
            WHERE photo NOT IN (SELECT id FROM photo)
        """)
        print(f"Deleted {orphaned_count} orphaned records")

    # Step 3: Rename old table
    db.execute_sql("ALTER TABLE importmeta RENAME TO importmeta_old")

    # Step 4: Create new table with proper foreign key
    db.execute_sql("""
        CREATE TABLE importmeta (
            id INTEGER PRIMARY KEY,
            sha1 TEXT NOT NULL UNIQUE,
            photo_id INTEGER NOT NULL,
            importpath TEXT,
            importsource TEXT,
            filedate DATETIME,
            s3 INTEGER,
            ts DATETIME NOT NULL,
            FOREIGN KEY (photo_id) REFERENCES photo(id) ON DELETE CASCADE
        )
    """)

    # Step 5: Copy data from old table (only valid records)
    print("Copying data from old table...")
    db.execute_sql("""
        INSERT INTO importmeta (id, sha1, photo_id, importpath, importsource, filedate, s3, ts)
        SELECT id, sha1, photo, importpath, importsource, filedate, s3, ts
        FROM importmeta_old
        WHERE photo IN (SELECT id FROM photo)
    """)

    # Step 5: Drop old table
    db.execute_sql("DROP TABLE importmeta_old")

    print("Migration complete!")
    print("ImportMeta now has CASCADE delete on photo relationship")

if __name__ == '__main__':
    try:
        migrate()
    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
