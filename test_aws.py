#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for AWS S3 functions
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import aws


class TestAWSFunctions(unittest.TestCase):
    """Test AWS S3 interaction functions"""

    def setUp(self):
        """Set up test config"""
        self.config = {
            'AWS_ACCESS_KEY_ID': 'test_key_id',
            'AWS_SECRET_ACCESS_KEY': 'test_secret_key',
            'S3_BUCKET_NAME': 'test-bucket'
        }

    @patch('aws.boto.connect_s3')
    def test_upload_to_s3_success(self, mock_connect):
        """Test successful upload to S3"""
        # Mock the S3 connection and bucket
        mock_conn = MagicMock()
        mock_bucket = MagicMock()
        mock_key = MagicMock()

        mock_connect.return_value = mock_conn
        mock_conn.get_bucket.return_value = mock_bucket

        # Create a test file
        import tempfile
        fd, temp_path = tempfile.mkstemp()
        import os
        os.write(fd, b'test content')
        os.close(fd)

        try:
            result = aws.uploadToS3(temp_path, 'test/key.jpg', self.config)

            self.assertTrue(result)
            mock_connect.assert_called_once_with('test_key_id', 'test_secret_key')
            mock_conn.get_bucket.assert_called_once_with('test-bucket')

        finally:
            os.unlink(temp_path)

    @patch('aws.boto.connect_s3')
    def test_upload_to_s3_with_policy(self, mock_connect):
        """Test upload with custom policy"""
        mock_conn = MagicMock()
        mock_bucket = MagicMock()

        mock_connect.return_value = mock_conn
        mock_conn.get_bucket.return_value = mock_bucket

        import tempfile
        fd, temp_path = tempfile.mkstemp()
        import os
        os.close(fd)

        try:
            result = aws.uploadToS3(
                temp_path,
                'test/key.jpg',
                self.config,
                policy='public-read'
            )

            self.assertTrue(result)

        finally:
            os.unlink(temp_path)

    @patch('aws.boto.connect_s3')
    def test_delete_from_s3(self, mock_connect):
        """Test deleting from S3"""
        mock_conn = MagicMock()
        mock_bucket = MagicMock()
        mock_key = MagicMock()

        mock_connect.return_value = mock_conn
        mock_conn.get_bucket.return_value = mock_bucket

        result = aws.deleteFromS3('test/key.jpg', self.config)

        # Should connect and attempt delete
        mock_connect.assert_called_once_with('test_key_id', 'test_secret_key')
        mock_conn.get_bucket.assert_called_once_with('test-bucket')

    @patch('aws.boto.connect_s3')
    def test_get_private_url(self, mock_connect):
        """Test generating private URL"""
        mock_conn = MagicMock()
        mock_bucket = MagicMock()
        mock_key = MagicMock()
        mock_key.generate_url.return_value = 'https://example.com/signed-url'

        mock_connect.return_value = mock_conn
        mock_conn.get_bucket.return_value = mock_bucket

        with patch('aws.Key') as mock_key_class:
            mock_key_class.return_value = mock_key

            result = aws.getPrivateURL(self.config, '/test/key.jpg')

            mock_key.generate_url.assert_called_once_with(10)
            self.assertEqual(result, 'https://example.com/signed-url')

    @patch('aws.boto.connect_s3')
    def test_get_private_url_exception(self, mock_connect):
        """Test private URL generation with exception"""
        mock_conn = MagicMock()
        mock_bucket = MagicMock()
        mock_key = MagicMock()
        mock_key.generate_url.side_effect = Exception('S3 Error')

        mock_connect.return_value = mock_conn
        mock_conn.get_bucket.return_value = mock_bucket

        with patch('aws.Key') as mock_key_class:
            mock_key_class.return_value = mock_key

            result = aws.getPrivateURL(self.config, '/test/key.jpg')

            self.assertIsNone(result)

    @patch('aws.boto.connect_s3')
    def test_create_s3_bucket(self, mock_connect):
        """Test creating S3 bucket"""
        mock_conn = MagicMock()
        mock_bucket = MagicMock()

        mock_connect.return_value = mock_conn
        mock_conn.create_bucket.return_value = mock_bucket

        with patch('aws.boto.s3.connection.Location') as mock_location:
            mock_location.DEFAULT = 'us-east-1'

            aws.createS3Bucket(self.config)

            mock_connect.assert_called_once_with('test_key_id', 'test_secret_key')
            mock_conn.create_bucket.assert_called_once()


if __name__ == '__main__':
    unittest.main()
