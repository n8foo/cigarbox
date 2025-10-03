#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test runner for CigarBox
Runs all unit tests and displays results
"""

import unittest
import sys
import os

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_all_tests():
    """Discover and run all tests"""
    # Create test loader
    loader = unittest.TestLoader()

    # Discover all test files
    start_dir = os.path.dirname(os.path.abspath(__file__))
    suite = loader.discover(start_dir, pattern='test_*.py')

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code based on results
    return 0 if result.wasSuccessful() else 1


def run_specific_test(test_module):
    """Run tests from a specific module"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(test_module)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # Run specific test module
        exit_code = run_specific_test(sys.argv[1])
    else:
        # Run all tests
        print("Running all CigarBox tests...\n")
        exit_code = run_all_tests()

    sys.exit(exit_code)
