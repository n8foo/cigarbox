#!/usr/bin/env python
"""Performance test suite for photo navigation queries

Usage:
    python perf/perf_test_navigation.py
    (or from perf directory: python perf_test_navigation.py)

This tests the navigation query performance across different contexts
(photostream, photosets, tags, dates) to identify bottlenecks.
"""
import sys
import os
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import db, Photo, PhotoPhotoset, PhotoTag, Tag, Photoset

def time_query(name, query_func):
    """Time a query function and return results"""
    start = time.time()
    result = query_func()
    elapsed = time.time() - start
    return elapsed, result

def test_photostream_navigation():
    """Test photostream navigation with privacy filters"""
    print("\n" + "="*60)
    print("PHOTOSTREAM NAVIGATION TEST")
    print("="*60)

    # Get a photo from the middle
    middle_id = Photo.select().order_by(Photo.id).offset(
        Photo.select().count() // 2
    ).limit(1).get().id

    photo = Photo.get_by_id(middle_id)
    print(f"Testing photo ID: {photo.id}")
    print(f"Total photos: {Photo.select().count():,}")

    # Simulate visible_levels (logged out user - NULL = public)
    visible_levels = []

    base_query = Photo.select().where(
        (Photo.privacy.is_null()) | (Photo.privacy.in_(visible_levels))
    )

    # Test next photo query
    elapsed, next_photo = time_query("Next photo", lambda: (
        base_query
        .where(Photo.id < photo.id)
        .order_by(Photo.id.desc())
        .limit(1)
        .first()
    ))
    print(f"\nNext photo query: {elapsed*1000:.2f}ms")
    print(f"  Result: ID {next_photo.id if next_photo else 'None'}")

    # Test prev photo query
    elapsed, prev_photo = time_query("Prev photo", lambda: (
        base_query
        .where(Photo.id > photo.id)
        .order_by(Photo.id.asc())
        .limit(1)
        .first()
    ))
    print(f"Previous photo query: {elapsed*1000:.2f}ms")
    print(f"  Result: ID {prev_photo.id if prev_photo else 'None'}")

    # Check indexes
    print("\n--- Index Analysis ---")
    cursor = db.execute_sql("""
        SELECT name, sql FROM sqlite_master
        WHERE type='index' AND tbl_name='photo'
    """)
    indexes = cursor.fetchall()
    print(f"Indexes on photo table: {len(indexes)}")
    for name, sql in indexes:
        if sql:
            print(f"  • {name}")

    # Check query plan
    print("\n--- Query Plan (Next Photo) ---")
    cursor = db.execute_sql("""
        EXPLAIN QUERY PLAN
        SELECT * FROM photo
        WHERE (privacy IS NULL OR privacy IN ())
        AND id < ?
        ORDER BY id DESC
        LIMIT 1
    """, (photo.id,))
    for row in cursor.fetchall():
        print(f"  {row}")

def test_photoset_navigation():
    """Test photoset navigation with datetaken ordering"""
    print("\n" + "="*60)
    print("PHOTOSET NAVIGATION TEST")
    print("="*60)

    # Find a photoset with photos
    photoset = (Photoset.select()
                .join(PhotoPhotoset)
                .group_by(Photoset.id)
                .order_by(Photoset.id)
                .limit(1)
                .get())

    photo_count = (PhotoPhotoset.select()
                   .where(PhotoPhotoset.photoset == photoset.id)
                   .count())

    print(f"Testing photoset: '{photoset.title}' (ID {photoset.id})")
    print(f"Photos in set: {photo_count}")

    # Get a photo from the middle of the set
    photo_in_set = (Photo.select()
                    .join(PhotoPhotoset)
                    .where(PhotoPhotoset.photoset == photoset.id)
                    .order_by(Photo.datetaken.asc())
                    .offset(photo_count // 2)
                    .limit(1)
                    .get())

    print(f"Testing photo ID: {photo_in_set.id}")

    visible_levels = []
    base_query = (Photo.select()
                  .join(PhotoPhotoset)
                  .where((PhotoPhotoset.photoset == photoset.id) &
                         ((Photo.privacy.is_null()) | (Photo.privacy.in_(visible_levels)))))

    current_datetaken = photo_in_set.datetaken

    # Test next photo query
    elapsed, next_photo = time_query("Next photo", lambda: (
        base_query
        .where((Photo.datetaken > current_datetaken) |
               ((Photo.datetaken == current_datetaken) & (Photo.id > photo_in_set.id)))
        .order_by(Photo.datetaken.asc(), Photo.id.asc())
        .limit(1)
        .first()
    ))
    print(f"\nNext photo query: {elapsed*1000:.2f}ms")
    print(f"  Result: ID {next_photo.id if next_photo else 'None'}")

    # Test prev photo query
    elapsed, prev_photo = time_query("Prev photo", lambda: (
        base_query
        .where((Photo.datetaken < current_datetaken) |
               ((Photo.datetaken == current_datetaken) & (Photo.id < photo_in_set.id)))
        .order_by(Photo.datetaken.desc(), Photo.id.desc())
        .limit(1)
        .first()
    ))
    print(f"Previous photo query: {elapsed*1000:.2f}ms")
    print(f"  Result: ID {prev_photo.id if prev_photo else 'None'}")

def test_tag_navigation():
    """Test tag navigation"""
    print("\n" + "="*60)
    print("TAG NAVIGATION TEST")
    print("="*60)

    # Find a tag with photos
    tag = (Tag.select()
           .join(PhotoTag)
           .group_by(Tag.id)
           .order_by(Tag.id)
           .limit(1)
           .get())

    photo_count = (PhotoTag.select()
                   .where(PhotoTag.tag == tag.id)
                   .count())

    print(f"Testing tag: '{tag.name}' (ID {tag.id})")
    print(f"Photos with tag: {photo_count}")

    # Get a photo from the middle
    photo_with_tag = (Photo.select()
                      .join(PhotoTag)
                      .where(PhotoTag.tag == tag.id)
                      .order_by(Photo.id.desc())
                      .offset(photo_count // 2)
                      .limit(1)
                      .get())

    print(f"Testing photo ID: {photo_with_tag.id}")

    visible_levels = []
    base_query = (Photo.select()
                  .join(PhotoTag)
                  .join(Tag)
                  .where((Tag.name == tag.name) &
                         ((Photo.privacy.is_null()) | (Photo.privacy.in_(visible_levels)))))

    # Test next photo query
    elapsed, next_photo = time_query("Next photo", lambda: (
        base_query
        .where(Photo.id < photo_with_tag.id)
        .order_by(Photo.id.desc())
        .limit(1)
        .first()
    ))
    print(f"\nNext photo query: {elapsed*1000:.2f}ms")

    # Test prev photo query
    elapsed, prev_photo = time_query("Prev photo", lambda: (
        base_query
        .where(Photo.id > photo_with_tag.id)
        .order_by(Photo.id.asc())
        .limit(1)
        .first()
    ))
    print(f"Previous photo query: {elapsed*1000:.2f}ms")

def main():
    """Run all performance tests"""
    print("\n" + "#"*60)
    print("# CIGARBOX NAVIGATION PERFORMANCE SUITE")
    print("#"*60)
    print(f"\nDatabase: {db.database}")
    print(f"Total photos: {Photo.select().count():,}")

    # Connect if not already connected
    if db.is_closed():
        db.connect()

    try:
        test_photostream_navigation()
        test_photoset_navigation()
        test_tag_navigation()

        print("\n" + "#"*60)
        print("# TESTS COMPLETE")
        print("#"*60)

    finally:
        db.close()

if __name__ == '__main__':
    main()
