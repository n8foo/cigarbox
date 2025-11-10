#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database migration script to add Proof-of-Work (PoW) tables

Adds bot protection via PoW CAPTCHA system.

Changes:
- Add powchallenge table - Stores active challenges (5-min expiry)
- Add powtoken table - Stores verified tokens (30-day expiry)

Safe to run multiple times - checks if tables already exist.
"""

import sys
import os

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from db import *

def migrate():
    """Run the migration"""
    print("Starting PoW tables migration...")

    # Check if tables already exist
    cursor = db.execute_sql("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name IN ('powchallenge', 'powtoken')
    """)
    existing = cursor.fetchall()
    existing_names = [row[0] for row in existing]

    if 'powchallenge' in existing_names and 'powtoken' in existing_names:
        print("✓ PoW tables already exist, skipping")
        return

    # Create tables if they don't exist
    if 'powchallenge' not in existing_names:
        print("Creating powchallenge table...")
        db.create_tables([PowChallenge], safe=True)
        print("✓ powchallenge table created")

    if 'powtoken' not in existing_names:
        print("Creating powtoken table...")
        db.create_tables([PowToken], safe=True)
        print("✓ powtoken table created")

    # Verify tables were created
    cursor = db.execute_sql("""
        SELECT name, sql FROM sqlite_master
        WHERE type='table' AND name IN ('powchallenge', 'powtoken')
        ORDER BY name
    """)
    tables = cursor.fetchall()

    print(f"\n✓ Created {len(tables)} tables:")
    for name, sql in tables:
        print(f"  • {name}")

    print("\n✓ Migration complete!")
    print("\nTo enable PoW protection:")
    print("  1. Set POW_ENABLED = True in config.py")
    print("  2. Set REQUIRE_AUTH_FOR_PHOTOS = False")
    print("  3. Restart web server")
    print("\nPoW will protect photo pages with 2-3 second challenge")

def main():
    """Main entry point"""
    print("="*60)
    print("Migration: Add Proof-of-Work bot protection tables")
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
