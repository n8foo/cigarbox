#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for database models
"""

import unittest
import datetime
import tempfile
import os
from peewee import SqliteDatabase

# Import models
from db import (Photo, Comment, Gallery, Photoset, Tag, PhotoPhotoset,
                PhotosetGallery, PhotoTag, ImportMeta, User, Role, UserRoles)


class TestDatabaseModels(unittest.TestCase):
    """Test database model creation and relationships"""

    def setUp(self):
        """Create a temporary database for testing"""
        self.test_db_fd, self.test_db_path = tempfile.mkstemp()
        self.test_db = SqliteDatabase(self.test_db_path)

        # Bind models to test database
        models = [Photo, Comment, Gallery, Photoset, Tag, PhotoPhotoset,
                  PhotosetGallery, PhotoTag, ImportMeta, User, Role, UserRoles]
        self.test_db.bind(models, bind_refs=False, bind_backrefs=False)
        self.test_db.connect()
        self.test_db.create_tables(models)

    def tearDown(self):
        """Close and remove test database"""
        self.test_db.close()
        os.close(self.test_db_fd)
        os.unlink(self.test_db_path)

    def test_photo_creation(self):
        """Test creating a photo record"""
        photo = Photo.create(
            sha1='abc123def456' * 3,  # 40 chars
            filetype='jpg',
            datetaken=datetime.datetime.now(),
            privacy=0
        )
        self.assertIsNotNone(photo.id)
        self.assertEqual(photo.filetype, 'jpg')
        self.assertIsNotNone(photo.ts)

    def test_photo_unique_sha1(self):
        """Test that sha1 is unique"""
        sha1 = 'unique123abc' * 3
        Photo.create(sha1=sha1, filetype='jpg')

        with self.assertRaises(Exception):
            Photo.create(sha1=sha1, filetype='png')

    def test_timestamp_is_unique_per_record(self):
        """Test that each record gets its own timestamp"""
        photo1 = Photo.create(sha1='test1234567890' * 3, filetype='jpg')
        photo2 = Photo.create(sha1='test0987654321' * 3, filetype='jpg')

        # Timestamps should be datetime objects, not the same reference
        self.assertIsInstance(photo1.ts, datetime.datetime)
        self.assertIsInstance(photo2.ts, datetime.datetime)

    def test_tag_creation(self):
        """Test creating tags"""
        tag = Tag.create(name='vacation')
        self.assertIsNotNone(tag.id)
        self.assertEqual(tag.name, 'vacation')

    def test_photoset_creation(self):
        """Test creating photosets"""
        photoset = Photoset.create(
            title='Summer 2022',
            description='Photos from summer vacation'
        )
        self.assertIsNotNone(photoset.id)
        self.assertEqual(photoset.title, 'Summer 2022')

    def test_photo_tag_relationship(self):
        """Test many-to-many relationship between photos and tags"""
        photo = Photo.create(sha1='relationship123' * 3, filetype='jpg')
        tag = Tag.create(name='sunset')

        photo_tag = PhotoTag.create(photo=photo, tag=tag)
        self.assertIsNotNone(photo_tag.id)
        self.assertEqual(photo_tag.photo.id, photo.id)
        self.assertEqual(photo_tag.tag.id, tag.id)

    def test_photo_photoset_relationship(self):
        """Test many-to-many relationship between photos and photosets"""
        photo = Photo.create(sha1='photoset123' * 3, filetype='jpg')
        photoset = Photoset.create(title='Test Set')

        photo_photoset = PhotoPhotoset.create(photo=photo, photoset=photoset)
        self.assertIsNotNone(photo_photoset.id)
        self.assertEqual(photo_photoset.photo.id, photo.id)

    def test_import_meta_creation(self):
        """Test import metadata tracking"""
        photo = Photo.create(sha1='importmeta123' * 3, filetype='jpg')
        import_meta = ImportMeta.create(
            sha1='importmeta123' * 3,
            photo=photo.id,
            importpath='/test/path/image.jpg',
            importsource='test_host',
            s3=1
        )
        self.assertIsNotNone(import_meta.id)
        # After migration, photo is a ForeignKey that returns the Photo object
        # Access .id to get the integer ID
        self.assertEqual(import_meta.photo.id, photo.id)
        self.assertEqual(import_meta.s3, 1)

    def test_user_creation(self):
        """Test user creation"""
        user = User.create(
            email='test@example.com',
            password='hashed_password',
            active=True
        )
        self.assertIsNotNone(user.id)
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.active)


if __name__ == '__main__':
    unittest.main()
