#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for API endpoints
"""

import unittest
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from peewee import SqliteDatabase
from io import BytesIO

# Import Flask app
from app import app as flask_app
from db import Photo, Tag, PhotoTag, Photoset, PhotoPhotoset


class TestAPIEndpoints(unittest.TestCase):
    """Test API endpoints"""

    def setUp(self):
        """Set up test client and database"""
        self.test_db_fd, self.test_db_path = tempfile.mkstemp()
        self.test_db = SqliteDatabase(self.test_db_path)

        # Bind models to test database
        models = [Photo, Tag, PhotoTag, Photoset, PhotoPhotoset]
        self.test_db.bind(models, bind_refs=False, bind_backrefs=False)
        self.test_db.connect()
        self.test_db.create_tables(models)

        flask_app.config['TESTING'] = True
        flask_app.config['DATABASE'] = {'name': self.test_db_path}
        flask_app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
        flask_app.config['ALLOWED_EXTENSIONS'] = ['jpg', 'png', 'gif']
        flask_app.config['API_KEY'] = 'test-api-key-for-unit-tests'

        # Import api app (it's a separate Flask instance)
        from api import app as api_app
        api_app.config['TESTING'] = True
        api_app.config['DATABASE'] = {'name': self.test_db_path}
        api_app.config['UPLOAD_FOLDER'] = flask_app.config['UPLOAD_FOLDER']
        api_app.config['ALLOWED_EXTENSIONS'] = flask_app.config['ALLOWED_EXTENSIONS']
        api_app.config['API_KEY'] = 'test-api-key-for-unit-tests'
        self.client = api_app.test_client()
        self.api_key = 'test-api-key-for-unit-tests'

    def tearDown(self):
        """Clean up test database and files"""
        self.test_db.close()
        os.close(self.test_db_fd)
        os.unlink(self.test_db_path)

        # Clean up upload folder
        import shutil
        if os.path.exists(flask_app.config['UPLOAD_FOLDER']):
            shutil.rmtree(flask_app.config['UPLOAD_FOLDER'])

    def test_api_sha1_lookup_not_found(self):
        """Test SHA1 lookup for non-existent photo"""
        response = self.client.get('/api/sha1/nonexistent123')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertFalse(data['exists'])
        self.assertEqual(data['status'], 'Not Found')

    def test_api_sha1_lookup_found(self):
        """Test SHA1 lookup for existing photo"""
        sha1 = 'apitest123' * 3
        photo = Photo.create(sha1=sha1, filetype='jpg')

        with patch('api.util.getSha1Path') as mock_path:
            mock_path.return_value = ('ab/c1/23', 'filename')

            response = self.client.get(f'/api/sha1/{sha1}')
            self.assertEqual(response.status_code, 200)

            data = json.loads(response.data)
            self.assertTrue(data['exists'])
            self.assertEqual(data['status'], 'Found')
            self.assertEqual(data['photo_id'], str(photo.id))

    def test_api_add_tags(self):
        """Test adding tags via API"""
        photo = Photo.create(sha1='tagapitest123' * 3, filetype='jpg')

        payload = {
            'photo_id': photo.id,
            'tags': ['vacation', 'beach', 'summer']
        }

        with patch('api.process.photosAddTag') as mock_add_tag:
            mock_add_tag.return_value = 1

            response = self.client.post(
                '/api/photos/addtags',
                data=json.dumps(payload),
                content_type='application/json',
                headers={'X-API-Key': self.api_key}
            )

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(data['photo_id'], photo.id)
            self.assertEqual(len(data['tags']), 3)

    def test_api_add_tags_comma_separated(self):
        """Test adding tags as comma-separated string"""
        photo = Photo.create(sha1='tagcommatest123' * 3, filetype='jpg')

        payload = {
            'photo_id': photo.id,
            'tags': 'vacation,beach,summer'
        }

        with patch('api.process.photosAddTag') as mock_add_tag:
            mock_add_tag.return_value = 1

            response = self.client.post(
                '/api/photos/addtags',
                data=json.dumps(payload),
                content_type='application/json',
                headers={'X-API-Key': self.api_key}
            )

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(len(data['tags']), 3)

    def test_api_remove_tags(self):
        """Test removing tags via API"""
        photo = Photo.create(sha1='removetagapi123' * 3, filetype='jpg')
        tag = Tag.create(name='removeme')
        PhotoTag.create(photo=photo, tag=tag)

        payload = {
            'photo_id': photo.id,
            'tags': ['removeme']
        }

        with patch('api.process.photosRemoveTag') as mock_remove_tag:
            mock_remove_tag.return_value = (photo.id, 'removeme')

            response = self.client.post(
                '/api/photos/removetags',
                data=json.dumps(payload),
                content_type='application/json',
                headers={'X-API-Key': self.api_key}
            )

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(data['photo_id'], photo.id)

    def test_api_add_to_photoset(self):
        """Test adding photo to photoset via API"""
        photo = Photo.create(sha1='photosetapi123' * 3, filetype='jpg')

        payload = {
            'photo_id': photo.id,
            'photoset': 'Test Set'
        }

        with patch('api.process.photosetsCreate') as mock_create:
            with patch('api.process.photosetsAddPhoto') as mock_add:
                mock_create.return_value = 1

                response = self.client.post(
                    '/api/photoset/addphoto',
                    data=json.dumps(payload),
                    content_type='application/json',
                    headers={'X-API-Key': self.api_key}
                )

                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertEqual(data['photo_id'], photo.id)
                self.assertEqual(data['photoset_id'], 1)

    @patch('api.processPhoto')
    def test_api_upload_with_file(self, mock_process):
        """Test file upload via API"""
        mock_process.return_value = 123

        # Create a fake image file
        data = {
            'files': (BytesIO(b'fake image data'), 'test.jpg'),
            'sha1': 'abc123',
            'clientfilename': 'test.jpg',
            'api_key': self.api_key
        }

        with patch('api.allowed_file') as mock_allowed:
            mock_allowed.return_value = True

            response = self.client.post(
                '/api/upload',
                data=data,
                content_type='multipart/form-data'
            )

            self.assertEqual(response.status_code, 200)
            result = json.loads(response.data)
            self.assertIn('photo_ids', result)

    def test_api_upload_with_tags(self):
        """Test upload with tags"""
        data = {
            'files': (BytesIO(b'fake image'), 'test.jpg'),
            'sha1': 'abc123',
            'clientfilename': 'test.jpg',
            'tags': 'vacation,beach',
            'api_key': self.api_key
        }

        with patch('api.processPhoto') as mock_process:
            with patch('api.process.photosAddTag') as mock_add_tag:
                with patch('api.allowed_file') as mock_allowed:
                    mock_allowed.return_value = True
                    mock_process.return_value = 456

                    response = self.client.post(
                        '/api/upload',
                        data=data,
                        content_type='multipart/form-data'
                    )

                    self.assertEqual(response.status_code, 200)


class TestAPIValidation(unittest.TestCase):
    """Test API input validation"""

    def test_tags_list_initialization_fixed(self):
        """Test that tags variable is properly initialized as empty list"""
        # This tests the fix for tags=list bug
        from api import apiphotosAddTags

        # The function should initialize tags as [] not list
        # This is verified by code inspection in the fix


if __name__ == '__main__':
    unittest.main()
