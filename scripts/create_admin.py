#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Create admin user for CigarBox

This script creates an admin user with:
- Admin role (can manage everything)
- Private permission level (can see all photos)
- Bcrypt-hashed password
"""

import sys
import os
import getpass
import uuid
import bcrypt

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from db import *

def create_admin():
    """Create admin user interactively"""
    print("=" * 60)
    print("CigarBox Admin User Creation")
    print("=" * 60)
    print()

    # Check config
    if not app.config.get('SECURITY_PASSWORD_SALT'):
        print("❌ ERROR: SECURITY_PASSWORD_SALT not set in config.py")
        print("   Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'")
        sys.exit(1)

    # Connect to database
    db.connect()

    # Check if admin role exists, create if not
    admin_role = Role.get_or_none(Role.name == 'admin')
    if not admin_role:
        print("Creating 'admin' role...")
        admin_role = Role.create(
            name='admin',
            description='Administrator with full access'
        )
        print("✓ Admin role created")

    # Get user details
    print()
    email = input("Admin email: ").strip()
    if not email:
        print("❌ Email is required")
        sys.exit(1)

    # Check if user already exists
    existing_user = User.get_or_none(User.email == email)
    if existing_user:
        print("❌ User with email '{}' already exists".format(email))
        response = input("Update this user to admin? [y/N]: ")
        if response.lower() != 'y':
            sys.exit(0)
        user = existing_user
    else:
        # Get password
        while True:
            password = getpass.getpass("Password: ")
            password_confirm = getpass.getpass("Confirm password: ")

            if not password:
                print("❌ Password is required")
                continue

            if password != password_confirm:
                print("❌ Passwords don't match, try again")
                continue

            break

        # Create user with bcrypt-hashed password
        print()
        print("Creating admin user...")
        # Hash password with bcrypt (matching Flask-Security's format)
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        user = User.create(
            email=email,
            password=password_hash,
            active=True,
            fs_uniquifier=str(uuid.uuid4()),
            permission_level='private'  # Can see all photos
        )
        print("✓ User created: {}".format(email))

    # Assign admin role if not already assigned
    user_role = UserRoles.get_or_none(
        (UserRoles.user == user) & (UserRoles.role == admin_role)
    )
    if not user_role:
        UserRoles.create(user=user, role=admin_role)
        print("✓ Admin role assigned")
    else:
        print("✓ User already has admin role")

    # Ensure permission level is set
    if not user.permission_level:
        user.permission_level = 'private'
        user.save()
        print("✓ Permission level set to 'private'")

    db.close()

    print()
    print("=" * 60)
    print("✅ Admin user ready!")
    print("=" * 60)
    print("Email: {}".format(email))
    print("Permission level: {} (sees all photos)".format(user.permission_level))
    print("Roles: admin")
    print()
    print("You can now login at: http://localhost:9600/login")
    print()

if __name__ == '__main__':
    try:
        create_admin()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled")
        sys.exit(1)
    except Exception as e:
        print("\n❌ Error: {}".format(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)
