#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for web routes
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
from peewee import SqliteDatabase

# Import Flask app and models
from app import app
from db import Photo, Tag, PhotoTag, Photoset, PhotoPhotoset


class TestWebRoutes(unittest.TestCase):
    """Test Flask web routes"""

    def setUp(self):
        """Set up test client and database"""
        self.test_db_fd, self.test_db_path = tempfile.mkstemp()
        self.test_db = SqliteDatabase(self.test_db_path)

        # Bind models to test database
        models = [Photo, Tag, PhotoTag, Photoset, PhotoPhotoset]
        self.test_db.bind(models, bind_refs=False, bind_backrefs=False)
        self.test_db.connect()
        self.test_db.create_tables(models)

        app.config['TESTING'] = True
        app.config['DATABASE'] = {'name': self.test_db_path}
        self.client = app.test_client()

    def tearDown(self):
        """Clean up test database"""
        self.test_db.close()
        os.close(self.test_db_fd)
        os.unlink(self.test_db_path)

    def test_index_route(self):
        """Test main index redirects to photostream"""
        response = self.client.get('/')
        self.assertIn(response.status_code, [200, 301, 302, 308])

    def test_404_handler(self):
        """Test 404 error handler"""
        response = self.client.get('/nonexistent-page')
        self.assertEqual(response.status_code, 404)

    def test_about_page(self):
        """Test about page"""
        response = self.client.get('/about')
        self.assertEqual(response.status_code, 200)

    def test_find_utility_function(self):
        """Test find utility function"""
        from web import find

        test_list = [
            {'id': 1, 'name': 'foo'},
            {'id': 2, 'name': 'bar'},
            {'id': 3, 'name': 'baz'}
        ]

        result = find(test_list, 'name', 'bar')
        self.assertEqual(result, 1)

    def test_bulk_edit_route_exists(self):
        """Test bulk edit route exists in app"""
        from web import app
        # Check that the route is registered
        rules = [str(rule) for rule in app.url_map.iter_rules()]
        self.assertTrue(any('/photos/bulk-edit' in rule for rule in rules),
                       "Bulk edit route not found in URL map")

    def test_allowed_file(self):
        """Test file extension validation"""
        from web import allowed_file

        # Mock config
        app.config['ALLOWED_EXTENSIONS'] = ['jpg', 'png', 'gif']

        self.assertTrue(allowed_file('photo.jpg'))
        self.assertTrue(allowed_file('image.PNG'))
        self.assertTrue(allowed_file('animation.gif'))
        self.assertFalse(allowed_file('document.pdf'))
        self.assertFalse(allowed_file('noextension'))

    @patch('web.Photo')
    def test_photostream_pagination(self, mock_photo):
        """Test photostream with pagination"""
        mock_query = MagicMock()
        mock_photo.select.return_value = mock_query
        mock_query.where.return_value = mock_query  # Privacy filtering
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 0  # For pagination metadata
        mock_query.paginate.return_value = []

        response = self.client.get('/photostream')
        self.assertEqual(response.status_code, 200)

    @patch('web.Tag')
    def test_tags_page(self, mock_tag):
        """Test tags listing page"""
        mock_query = MagicMock()
        mock_tag.select.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.group_by.return_value = []

        response = self.client.get('/tags')
        self.assertEqual(response.status_code, 200)

    def test_upload_form(self):
        """Test upload form page requires login"""
        response = self.client.get('/upload')
        # Should redirect to login page since @login_required decorator is applied
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)


class TestPhotoOperations(unittest.TestCase):
    """Test photo-specific operations"""

    def setUp(self):
        """Set up test database"""
        self.test_db_fd, self.test_db_path = tempfile.mkstemp()
        self.test_db = SqliteDatabase(self.test_db_path)

        models = [Photo, Tag, PhotoTag, Photoset, PhotoPhotoset]
        self.test_db.bind(models, bind_refs=False, bind_backrefs=False)
        self.test_db.connect()
        self.test_db.create_tables(models)

        app.config['TESTING'] = True
        app.config['DATABASE'] = {'name': self.test_db_path}
        self.client = app.test_client()

    def tearDown(self):
        """Clean up"""
        self.test_db.close()
        os.close(self.test_db_fd)
        os.unlink(self.test_db_path)

    def test_show_photo_by_id(self):
        """Test viewing a single photo"""
        photo = Photo.create(sha1='viewtest123' * 3, filetype='jpg')

        with patch('web.getSha1Path') as mock_path:
            mock_path.return_value = ('ab/c1/23', 'filename')

            response = self.client.get(f'/photos/{photo.id}')
            self.assertEqual(response.status_code, 200)

    def test_show_photo_by_sha1(self):
        """Test viewing photo by SHA1"""
        sha1 = 'sha1viewtest123' * 3
        photo = Photo.create(sha1=sha1, filetype='jpg')

        with patch('web.getSha1Path') as mock_path:
            mock_path.return_value = ('ab/c1/23', 'filename')

            response = self.client.get(f'/sha1/{sha1}')
            self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
