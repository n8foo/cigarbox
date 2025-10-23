#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database migration script to add authentication fields

Adds:
- User.fs_uniquifier (required by Flask-Security-Too 5.x)
- User.permission_level ('private', 'family', 'friends', 'public')
- Photo.uploaded_by (foreign key to User)
- ShareToken table (for temporary photo sharing)

Safe to run multiple times - checks if columns/tables exist first.
"""

import sys
import os

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from db import *
import uuid

def column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    cursor = db.execute_sql("PRAGMA table_info({})".format(table_name))
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def table_exists(table_name):
    """Check if a table exists"""
    cursor = db.execute_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None

def migrate():
    """Run the migration"""
    print("🔄 Starting database migration...")
    print("   Database: {}".format(app.config['DATABASE']['name']))

    # Connect to database
    db.connect()

    # 1. Add fs_uniquifier to User table
    if not column_exists('user', 'fs_uniquifier'):
        print("   Adding User.fs_uniquifier column...")
        db.execute_sql('ALTER TABLE user ADD COLUMN fs_uniquifier VARCHAR(255)')

        # Generate unique identifiers for existing users using raw SQL
        cursor = db.execute_sql('SELECT id FROM user')
        user_ids = [row[0] for row in cursor.fetchall()]
        for user_id in user_ids:
            uniquifier = str(uuid.uuid4())
            db.execute_sql('UPDATE user SET fs_uniquifier = ? WHERE id = ?', (uniquifier, user_id))
        print("   ✓ Added fs_uniquifier to {} existing users".format(len(user_ids)))
    else:
        print("   ✓ User.fs_uniquifier already exists")

    # 2. Add permission_level to User table
    if not column_exists('user', 'permission_level'):
        print("   Adding User.permission_level column...")
        db.execute_sql('ALTER TABLE user ADD COLUMN permission_level VARCHAR(50)')
        print("   ✓ Added User.permission_level (defaults to NULL)")
    else:
        print("   ✓ User.permission_level already exists")

    # 3. Add uploaded_by to Photo table
    if not column_exists('photo', 'uploaded_by_id'):
        print("   Adding Photo.uploaded_by_id column...")
        db.execute_sql('ALTER TABLE photo ADD COLUMN uploaded_by_id INTEGER')
        print("   ✓ Added Photo.uploaded_by_id (existing photos will be NULL)")
    else:
        print("   ✓ Photo.uploaded_by_id already exists")

    # 4. Create ShareToken table
    if not table_exists('sharetoken'):
        print("   Creating ShareToken table...")
        db.create_tables([ShareToken])
        print("   ✓ Created ShareToken table")
    else:
        print("   ✓ ShareToken table already exists")

    db.close()
    print("✅ Migration complete!")
    print()
    print("Next steps:")
    print("1. Run: python cli/create_admin.py")
    print("2. Test login at: http://localhost:9600/login")

if __name__ == '__main__':
    try:
        migrate()
    except Exception as e:
        print("❌ Migration failed: {}".format(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)
