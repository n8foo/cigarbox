#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for utility functions
"""

import unittest
import tempfile
import os
import hashlib
from PIL import Image

import util


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions"""

    def test_normalize_string(self):
        """Test string normalization"""
        self.assertEqual(util.normalizeString('Hello World'), 'helloworld')
        self.assertEqual(util.normalizeString('Test-Tag_123'), 'testtag_123')
        self.assertEqual(util.normalizeString('Special!@#$%'), 'special')

    def test_get_sha1_path(self):
        """Test SHA1 path generation"""
        sha1 = 'abc123def456' * 4  # 48 chars, but only first 40 used
        sha1_path, filename = util.getSha1Path(sha1[:40])

        self.assertEqual(sha1_path, 'ab/c1/23')
        self.assertEqual(filename, 'def456abc123def456abc123def456abc1')

    def test_hashfile(self):
        """Test file hashing"""
        # Create a temporary file
        fd, temp_path = tempfile.mkstemp()
        try:
            test_content = b'Test file content for hashing'
            os.write(fd, test_content)
            os.close(fd)

            # Calculate hash using our function
            result_hash = util.hashfile(temp_path)

            # Calculate expected hash
            expected_hash = hashlib.sha1(test_content).hexdigest()

            self.assertEqual(result_hash, expected_hash)
        finally:
            os.unlink(temp_path)

    def test_b58_encode_decode(self):
        """Test base58 encoding and decoding"""
        test_number = 12345
        encoded = util.b58encode(test_number)
        decoded = util.b58decode(encoded)

        self.assertEqual(decoded, test_number)
        self.assertIsInstance(encoded, str)

    def test_b58_encode_zero(self):
        """Test base58 encoding of zero"""
        result = util.b58encode(0)
        self.assertEqual(result, '1')

    def test_get_archive_uri(self):
        """Test archive URI generation"""
        sha1 = 'abc123def456' * 4
        sha1 = sha1[:40]
        archive_path = '/archive'

        uri = util.getArchiveURI(sha1, archive_path, 'jpg')
        expected = '/archive/ab/c1/23/def456abc123def456abc123def456abc1.jpg'

        self.assertEqual(uri, expected)

    def test_gen_thumbnail_creates_correct_filename(self):
        """Test thumbnail filename generation"""
        # Create a test image
        img = Image.new('RGB', (800, 600), color='red')
        fd, temp_path = tempfile.mkstemp(suffix='.jpg')
        os.close(fd)

        try:
            img.save(temp_path)

            # Create config mock
            config = {'LOCALARCHIVEPATH': os.path.dirname(temp_path)}

            # Get just the filename
            filename = os.path.basename(temp_path)

            # Generate thumbnail
            thumb_filename = util.genThumbnail(filename, 't', config, regen=True)

            expected_prefix = filename.split('.')[0] + '_t.'
            self.assertTrue(thumb_filename.startswith(expected_prefix))

        finally:
            os.unlink(temp_path)
            # Clean up thumbnail if created
            thumb_path = temp_path.replace('.jpg', '_t.jpg')
            if os.path.exists(thumb_path):
                os.unlink(thumb_path)

    def test_get_exif_tags_no_exif(self):
        """Test EXIF extraction from image without EXIF data"""
        # Create a simple image without EXIF
        img = Image.new('RGB', (100, 100), color='blue')
        fd, temp_path = tempfile.mkstemp(suffix='.jpg')
        os.close(fd)

        try:
            img.save(temp_path)
            exif = util.getExifTags(temp_path)

            # Should return None for images without EXIF
            self.assertIsNone(exif)

        finally:
            os.unlink(temp_path)


class TestGPSProcessing(unittest.TestCase):
    """Test GPS coordinate processing with error handling"""

    def test_missing_gps_fields(self):
        """Test that missing GPS fields don't crash"""
        # Create image without GPS data
        img = Image.new('RGB', (100, 100))
        fd, temp_path = tempfile.mkstemp(suffix='.jpg')
        os.close(fd)

        try:
            img.save(temp_path)
            result = util.getExifTags(temp_path)

            # Should handle gracefully
            self.assertIsNone(result)

        finally:
            os.unlink(temp_path)


if __name__ == '__main__':
    unittest.main()
