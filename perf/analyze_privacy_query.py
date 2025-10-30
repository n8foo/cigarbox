#!/usr/bin/env python
"""Analyze privacy query optimization and index usage

This helps understand why queries with privacy filters may or may not
use the privacy index, especially with OR conditions and NULL values.

Usage:
    python perf/analyze_privacy_query.py
    (or from perf directory: python analyze_privacy_query.py)
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import db

def main():
    """Analyze query plans for privacy-filtered queries"""
    print("="*60)
    print("PRIVACY QUERY OPTIMIZATION ANALYSIS")
    print("="*60)

    db.connect() if db.is_closed() else None

    # Check data distribution first
    print("\n1. Data distribution:")
    total = db.execute_sql('SELECT COUNT(*) FROM photo').fetchone()[0]
    privacy_2 = db.execute_sql('SELECT COUNT(*) FROM photo WHERE privacy=2').fetchone()[0]
    privacy_null = db.execute_sql('SELECT COUNT(*) FROM photo WHERE privacy IS NULL').fetchone()[0]
    privacy_combined = db.execute_sql('SELECT COUNT(*) FROM photo WHERE privacy=2 OR privacy IS NULL').fetchone()[0]

    print(f"   Total photos: {total:,}")
    print(f"   privacy=2 (family): {privacy_2:,} ({privacy_2/total*100:.1f}%)")
    print(f"   privacy IS NULL (public): {privacy_null:,} ({privacy_null/total*100:.1f}%)")
    print(f"   Combined (2 OR NULL): {privacy_combined:,} ({privacy_combined/total*100:.1f}%)")

    # Test different query patterns
    print("\n2. Query plan comparison:\n")

    # Current query (with OR and IS NULL)
    print("   a) Current query: (privacy IS NULL OR privacy IN (2))")
    cursor = db.execute_sql("""
    EXPLAIN QUERY PLAN
    SELECT * FROM photo
    WHERE (privacy IS NULL OR privacy IN (2)) AND id > 20000
    ORDER BY id ASC
    LIMIT 1
    """)
    for row in cursor.fetchall():
        print(f"      {row}")

    # Alternative: Just privacy = 2 (most common case)
    print("\n   b) Simplified query: privacy = 2 only")
    cursor = db.execute_sql("""
    EXPLAIN QUERY PLAN
    SELECT * FROM photo
    WHERE privacy = 2 AND id > 20000
    ORDER BY id ASC
    LIMIT 1
    """)
    for row in cursor.fetchall():
        print(f"      {row}")

    # Alternative: Use UNION for OR conditions
    print("\n   c) UNION approach: Separate queries for NULL and 2")
    cursor = db.execute_sql("""
    EXPLAIN QUERY PLAN
    SELECT * FROM (
        SELECT * FROM photo WHERE privacy = 2 AND id > 20000
        UNION
        SELECT * FROM photo WHERE privacy IS NULL AND id > 20000
    )
    ORDER BY id ASC
    LIMIT 1
    """)
    for row in cursor.fetchall():
        print(f"      {row}")

    # Check existing indexes
    print("\n3. Current indexes on photo table:")
    cursor = db.execute_sql("""
        SELECT name, sql FROM sqlite_master
        WHERE type='index' AND tbl_name='photo'
    """)
    indexes = cursor.fetchall()
    for name, sql in indexes:
        if sql:  # Skip auto-created indexes
            print(f"   • {name}")

    print("\n" + "="*60)
    print("ANALYSIS COMPLETE")
    print("="*60)

    db.close()

if __name__ == '__main__':
    main()
