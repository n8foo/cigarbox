#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration tests for cli/upload.py CLI tool
Tests against actual deployed Docker instance
"""

import unittest
import tempfile
import os
import sys
from PIL import Image
import subprocess
import json


class TestUploadIntegration(unittest.TestCase):
    """Integration tests for upload.py against Docker deployment"""

    def setUp(self):
        """Set up test fixtures"""
        # Get API URL from environment (set by fab test from fabric.yaml)
        # Falls back to localhost if not set (for local Docker testing)
        self.api_url = os.environ.get('CIGARBOX_TEST_API', 'http://localhost:8088/api')
        self.test_files = []

    def tearDown(self):
        """Clean up test files"""
        for test_file in self.test_files:
            if os.path.exists(test_file):
                os.unlink(test_file)

    def create_test_image(self, name='test_image.jpg'):
        """Create a test image file"""
        img = Image.new('RGB', (100, 100), color='red')
        fd, temp_path = tempfile.mkstemp(suffix='.jpg', prefix=name.replace('.jpg', '_'))
        os.close(fd)
        img.save(temp_path)
        self.test_files.append(temp_path)
        return temp_path

    def test_upload_new_photo(self):
        """Test uploading a new photo via CLI"""
        test_image = self.create_test_image('integration_test_new.jpg')

        # Run cli/upload.py as subprocess
        result = subprocess.run([
            sys.executable, 'cli/upload.py',
            '--files', test_image,
            '--tags', 'integration_test,automated',
            '--apiurl', self.api_url,
            '--privacy', 'public'
        ], capture_output=True, text=True)

        # Check it succeeded
        self.assertEqual(result.returncode, 0, f"Upload failed: {result.stderr}")
        self.assertIn('finished!', result.stderr.lower())

    def test_upload_duplicate_photo(self):
        """Test uploading the same photo twice (should skip second upload)"""
        test_image = self.create_test_image('integration_test_duplicate.jpg')

        # Upload first time
        result1 = subprocess.run([
            sys.executable, 'cli/upload.py',
            '--files', test_image,
            '--tags', 'integration_test,duplicate',
            '--apiurl', self.api_url
        ], capture_output=True, text=True)

        self.assertEqual(result1.returncode, 0)

        # Upload second time - should detect as existing
        result2 = subprocess.run([
            sys.executable, 'cli/upload.py',
            '--files', test_image,
            '--tags', 'integration_test,duplicate',
            '--apiurl', self.api_url
        ], capture_output=True, text=True)

        self.assertEqual(result2.returncode, 0)
        self.assertIn('already uploaded', result2.stderr.lower())

    def test_upload_with_photoset(self):
        """Test uploading to a photoset"""
        test_image = self.create_test_image('integration_test_photoset.jpg')

        result = subprocess.run([
            sys.executable, 'cli/upload.py',
            '--files', test_image,
            '--photoset', 'Integration Test Set',
            '--tags', 'integration_test',
            '--apiurl', self.api_url
        ], capture_output=True, text=True)

        self.assertEqual(result.returncode, 0)
        self.assertIn('finished!', result.stderr.lower())

    def test_upload_with_dirtag(self):
        """Test uploading with directory-based tagging"""
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        test_subdir = os.path.join(temp_dir, 'vacation_photos')
        os.makedirs(test_subdir)

        # Create image in subdirectory
        img = Image.new('RGB', (100, 100), color='blue')
        test_image = os.path.join(test_subdir, 'vacation.jpg')
        img.save(test_image)
        self.test_files.append(test_image)

        result = subprocess.run([
            sys.executable, 'cli/upload.py',
            '--files', test_image,
            '--dirtag',
            '--apiurl', self.api_url
        ], capture_output=True, text=True)

        self.assertEqual(result.returncode, 0)
        # Should have tagged with 'vacation_photos'
        self.assertIn('vacation_photos', result.stderr.lower())

        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)

    def test_upload_dryrun(self):
        """Test dry run mode doesn't actually upload"""
        test_image = self.create_test_image('integration_test_dryrun.jpg')

        result = subprocess.run([
            sys.executable, 'cli/upload.py',
            '--files', test_image,
            '--dryrun',
            '--apiurl', self.api_url
        ], capture_output=True, text=True)

        self.assertEqual(result.returncode, 0)
        self.assertIn('dryrun', result.stderr.lower())

    def test_upload_multiple_photos(self):
        """Test uploading multiple photos at once"""
        test_image1 = self.create_test_image('integration_test_multi1.jpg')
        test_image2 = self.create_test_image('integration_test_multi2.jpg')

        result = subprocess.run([
            sys.executable, 'cli/upload.py',
            '--files', test_image1, test_image2,
            '--tags', 'integration_test,multi_upload',
            '--apiurl', self.api_url
        ], capture_output=True, text=True)

        self.assertEqual(result.returncode, 0)
        # Should see two uploads
        self.assertEqual(result.stderr.lower().count('finished!'), 2)


if __name__ == '__main__':
    unittest.main()
