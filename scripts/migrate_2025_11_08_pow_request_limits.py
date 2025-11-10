#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database migration script to add request tracking to PoW tokens

Enhances PoW bot protection with request limits and IP binding.

Changes:
- Add powtoken.request_count - Track photo views per token (limit: 50)
- Add powtoken.last_request_at - Track last usage for time-based expiry (limit: 15 min)

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
    print("Starting PoW request limits migration...")

    # Check if powtoken table exists
    cursor = db.execute_sql("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='powtoken'
    """)
    if not cursor.fetchone():
        print("✗ powtoken table does not exist. Run migrate_2025_11_07_add_pow_tables.py first")
        return False

    # Check if columns already exist
    cursor = db.execute_sql("PRAGMA table_info(powtoken)")
    columns = [row[1] for row in cursor.fetchall()]

    needs_request_count = 'request_count' not in columns
    needs_last_request_at = 'last_request_at' not in columns

    if not needs_request_count and not needs_last_request_at:
        print("✓ PoW request tracking columns already exist, skipping")
        return True

    # Add missing columns
    if needs_request_count:
        print("Adding request_count column...")
        db.execute_sql("""
            ALTER TABLE powtoken ADD COLUMN request_count INTEGER DEFAULT 0
        """)
        print("✓ request_count column added")

    if needs_last_request_at:
        print("Adding last_request_at column...")
        db.execute_sql("""
            ALTER TABLE powtoken ADD COLUMN last_request_at DATETIME NULL
        """)
        print("✓ last_request_at column added")

    # Verify columns were added
    cursor = db.execute_sql("PRAGMA table_info(powtoken)")
    columns_after = cursor.fetchall()

    print(f"\n✓ powtoken table now has {len(columns_after)} columns:")
    for col_id, name, type_, not_null, default, pk in columns_after:
        print(f"  • {name} ({type_})")

    print("\n✓ Migration complete!")
    print("\nEnhanced PoW Protection:")
    print("  • Tokens limited to 50 photo views")
    print("  • Tokens expire after 15 minutes")
    print("  • IP binding enforced (token invalid if IP changes)")
    print("\nUpdate config.py:")
    print("  POW_TOKEN_EXPIRY_MINUTES = 15")
    print("  POW_TOKEN_MAX_REQUESTS = 50")
    print("  POW_BIND_TO_IP = True")

    return True

def main():
    """Main entry point"""
    print("="*60)
    print("Migration: Add PoW request tracking and limits")
    print("="*60)
    print()

    try:
        success = migrate()
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
