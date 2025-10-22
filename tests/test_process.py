#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for photo processing functions
"""

import unittest
import tempfile
import os
import datetime
from unittest.mock import Mock, patch, MagicMock
from peewee import SqliteDatabase

# Import the modules we're testing
import process
from db import Photo, Tag, PhotoTag, Photoset, PhotoPhotoset, ImportMeta


class TestProcessFunctions(unittest.TestCase):
    """Test photo processing functions"""

    def setUp(self):
        """Create a temporary database for testing"""
        self.test_db_fd, self.test_db_path = tempfile.mkstemp()
        self.test_db = SqliteDatabase(self.test_db_path)

        # Bind models to test database
        models = [Photo, Tag, PhotoTag, Photoset, PhotoPhotoset, ImportMeta]
        self.test_db.bind(models, bind_refs=False, bind_backrefs=False)
        self.test_db.connect()
        self.test_db.create_tables(models)

    def tearDown(self):
        """Close and remove test database"""
        self.test_db.close()
        os.close(self.test_db_fd)
        os.unlink(self.test_db_path)

    def test_get_file_type(self):
        """Test file type extraction"""
        self.assertEqual(process.getfileType('photo.jpg'), 'jpg')
        self.assertEqual(process.getfileType('photo.JPG'), 'jpg')
        self.assertEqual(process.getfileType('image.png'), 'png')
        self.assertEqual(process.getfileType('/path/to/file.jpeg'), 'jpeg')

    def test_add_photo_to_db(self):
        """Test adding photo to database"""
        sha1 = 'test123abc456' * 3
        file_type = 'jpg'
        date_taken = datetime.datetime.now()

        photo_id = process.addPhotoToDB(sha1, file_type, date_taken)

        self.assertIsNotNone(photo_id)
        photo = Photo.get(Photo.id == photo_id)
        self.assertEqual(photo.sha1, sha1)
        self.assertEqual(photo.filetype, file_type)

    def test_add_photo_duplicate_sha1(self):
        """Test adding photo with duplicate SHA1 returns existing ID"""
        sha1 = 'duplicate123' * 3
        file_type = 'jpg'
        date_taken = datetime.datetime.now()

        photo_id_1 = process.addPhotoToDB(sha1, file_type, date_taken)
        photo_id_2 = process.addPhotoToDB(sha1, file_type, date_taken)

        self.assertEqual(photo_id_1, photo_id_2)

    def test_photosets_create(self):
        """Test photoset creation"""
        title = 'Test Photoset'
        description = 'Test Description'

        photoset_id = process.photosetsCreate(title, description)

        self.assertIsNotNone(photoset_id)
        photoset = Photoset.get(Photoset.id == photoset_id)
        self.assertEqual(photoset.title, title)
        self.assertEqual(photoset.description, description)

    def test_photosets_create_duplicate_title(self):
        """Test creating photoset with duplicate title returns existing ID"""
        title = 'Duplicate Photoset'

        photoset_id_1 = process.photosetsCreate(title)
        photoset_id_2 = process.photosetsCreate(title)

        self.assertEqual(photoset_id_1, photoset_id_2)

    def test_photosets_add_photo(self):
        """Test adding photo to photoset"""
        # Create photo and photoset
        photo = Photo.create(sha1='addphoto123' * 3, filetype='jpg')
        photoset = Photoset.create(title='Test Set')

        # Add photo to photoset
        result = process.photosetsAddPhoto(photoset.id, photo.id)

        # Verify relationship exists
        relationship = PhotoPhotoset.get(
            PhotoPhotoset.photo == photo.id,
            PhotoPhotoset.photoset == photoset.id
        )
        self.assertIsNotNone(relationship)

    def test_photosets_add_photo_duplicate(self):
        """Test adding same photo to photoset twice returns True"""
        photo = Photo.create(sha1='duplicate456' * 3, filetype='jpg')
        photoset = Photoset.create(title='Duplicate Test')

        result1 = process.photosetsAddPhoto(photoset.id, photo.id)
        result2 = process.photosetsAddPhoto(photoset.id, photo.id)

        self.assertTrue(result2)

    def test_photos_add_tag(self):
        """Test adding tag to photo"""
        photo = Photo.create(sha1='tagtest123' * 3, filetype='jpg')
        tag_name = 'Vacation'

        tag_id = process.photosAddTag(photo.id, tag_name)

        self.assertIsNotNone(tag_id)

        # Verify tag was normalized
        tag = Tag.get(Tag.name == 'vacation')
        self.assertEqual(tag.name, 'vacation')

        # Verify relationship
        photo_tag = PhotoTag.get(
            PhotoTag.photo == photo.id,
            PhotoTag.tag == tag.id
        )
        self.assertIsNotNone(photo_tag)

    def test_photos_add_tag_normalizes(self):
        """Test that tag names are normalized"""
        photo = Photo.create(sha1='normalize123' * 3, filetype='jpg')

        tag_id1 = process.photosAddTag(photo.id, 'Test Tag!')
        tag_id2 = process.photosAddTag(photo.id, 'test-tag')

        # Both should map to the same normalized tag
        tag = Tag.get(Tag.name == 'testtag')
        self.assertIsNotNone(tag)

    def test_photos_remove_tag(self):
        """Test removing tag from photo"""
        photo = Photo.create(sha1='removetag123' * 3, filetype='jpg')
        tag = Tag.create(name='removeme')
        PhotoTag.create(photo=photo, tag=tag)

        result = process.photosRemoveTag(photo.id, 'removeme')

        # Verify relationship is removed
        count = PhotoTag.select().where(
            PhotoTag.photo == photo.id,
            PhotoTag.tag == tag.id
        ).count()
        self.assertEqual(count, 0)

    def test_photos_remove_nonexistent_tag(self):
        """Test removing tag that doesn't exist"""
        photo = Photo.create(sha1='notag123' * 3, filetype='jpg')

        # Should not raise exception
        result = process.photosRemoveTag(photo.id, 'nonexistent')
        self.assertIsNotNone(result)

    def test_get_sha1_from_photo_id(self):
        """Test retrieving SHA1 from photo ID"""
        sha1 = 'getsha1test123' * 3
        photo = Photo.create(sha1=sha1, filetype='jpg')

        result = process.getSha1FromPhotoID(photo.id)

        self.assertEqual(result, sha1)

    def test_get_photo_id_from_sha1(self):
        """Test retrieving photo ID from SHA1"""
        sha1 = 'getidtest123' * 3
        photo = Photo.create(sha1=sha1, filetype='jpg')

        result = process.getPhotoIDFromSha1(sha1)

        self.assertEqual(result, photo.id)

    def test_check_import_status_s3_true(self):
        """Test checking if photo was imported to S3"""
        photo = Photo.create(sha1='s3test123' * 3, filetype='jpg')
        ImportMeta.create(
            sha1=photo.sha1,
            photo=photo.id,
            s3=True
        )

        result = process.checkImportStatusS3(photo.id)

        self.assertTrue(result)

    def test_check_import_status_s3_false(self):
        """Test S3 status when not uploaded"""
        photo = Photo.create(sha1='nos3test123' * 3, filetype='jpg')

        result = process.checkImportStatusS3(photo.id)

        self.assertFalse(result)

    @patch('process.app')
    def test_set_photo_privacy(self, mock_app):
        """Test setting photo privacy"""
        mock_app.config = {'PRIVACYFLAGS': {'private': 8}}

        photo = Photo.create(sha1='privacytest123' * 3, filetype='jpg', privacy=0)

        result = process.setPhotoPrivacy(photo.id, 'private')

        self.assertTrue(result)
        photo_updated = Photo.get(Photo.id == photo.id)
        self.assertEqual(photo_updated.privacy, 8)

    def test_replace_photo(self):
        """Test replacing photo data"""
        old_sha1 = 'oldphoto123' * 3
        new_sha1 = 'newphoto123' * 3
        photo = Photo.create(sha1=old_sha1, filetype='jpg')

        new_date = datetime.datetime.now()
        result = process.replacePhoto(photo.id, new_sha1, 'png', new_date)

        self.assertEqual(result, new_sha1)
        updated_photo = Photo.get(Photo.id == photo.id)
        self.assertEqual(updated_photo.sha1, new_sha1)
        self.assertEqual(updated_photo.filetype, 'png')


if __name__ == '__main__':
    unittest.main()
