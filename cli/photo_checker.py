#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Photo Checker
~~~~~~~~~~~~~

Scans a directory hierarchy and checks which photos are already uploaded
to CigarBox by comparing SHA1 hashes via the API.

Usage:
    # Find photos NOT yet uploaded
    python photo_checker.py ~/Photos --api-url http://testserver:8088/api

    # Show what IS already uploaded
    python photo_checker.py ~/Photos --api-url http://testserver:8088/api --show-found

:copyright: (c) 2015 by Nathan Hubbard @n8foo.
:license: Apache, see LICENSE for more details.
"""

import os
import argparse
import hashlib
import requests

def calculate_sha1(file_path):
    """Calculate SHA1 hash of a file.

    Args:
        file_path: Path to the file to hash

    Returns:
        SHA1 hex digest string
    """
    sha1 = hashlib.sha1()
    with open(file_path, "rb") as f:
        while True:
            data = f.read(65536)  # Read in 64k chunks
            if not data:
                break
            sha1.update(data)
    return sha1.hexdigest()

def check_file_with_api(api_url, file_path):
    """Check if a file exists in CigarBox via API.

    Args:
        api_url: Base URL of the CigarBox API
        file_path: Path to the file to check

    Returns:
        JSON response dict with 'exists', 'photo_id', and 'path' keys
    """
    sha1 = calculate_sha1(file_path)
    response = requests.get(f"{api_url}/sha1/{sha1}")
    return response.json()

def main():
    """Main program - scan directory and check files against API."""
    parser = argparse.ArgumentParser(description="Check files in a directory hierarchy with an API")
    parser.add_argument("directory", help="Directory to search through")
    parser.add_argument("--api-url", default="http://localhost:9601/api", help="URL of the API")
    parser.add_argument("--web-url", default="http://localhost:9600", help="URL of the Web App")
    parser.add_argument("--show-found", action="store_true", help="Show information about found photos")
    args = parser.parse_args()

    # Static array of filenames to ignore
    ignore_filenames = [".DS_Store"]

    for root, dirs, files in os.walk(args.directory):
        for file_name in files:
            if file_name in ignore_filenames:
                continue  # Ignore this file
            file_path = os.path.join(root, file_name)
            response = check_file_with_api(args.api_url, file_path)
            
            if response["exists"]:
                if args.show_found:
                    photo_id = response["photo_id"]
                    print(f"File found: {file_path}, Photo URL: {args.web_url}/photos/{photo_id}")
            elif not args.show_found:
                print(f"File not found: {file_path}")

if __name__ == "__main__":
    main()
