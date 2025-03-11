#!/usr/bin/env python
"""
Standalone test runner for scenario-based tests.

This script serves as the main entry point for running all scenario-based
tests or specific test suites based on command-line arguments.
"""

import os
import sys
import argparse
import unittest
import logging
from typing import List, Optional

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from tests.scenarios.test_utils import logger

# Import all test modules - add new modules here as they are created
from tests.scenarios.test_order_queries import TestOrderQueries

def get_all_test_cases() -> List[unittest.TestCase]:
    """Return a list of all available test cases."""
    return [
        TestOrderQueries,
        # Add more test case classes here
    ]

def run_all_tests(verbosity: int = 2) -> bool:
    """
    Run all scenario tests.
    
    Args:
        verbosity: Level of detail in test output (0-3)
        
    Returns:
        Boolean indicating test success
    """
    logger.info("Running all scenario tests")
    
    # Create a test suite with all test cases
    suite = unittest.TestSuite()
    
    for test_case in get_all_test_cases():
        suite.addTest(unittest.makeSuite(test_case))
    
    # Run the suite
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_specific_tests(test_names: List[str], verbosity: int = 2) -> bool:
    """
    Run specific tests by name.
    
    Args:
        test_names: List of test names to run (format: 'TestClass.test_method')
        verbosity: Level of detail in test output (0-3)
        
    Returns:
        Boolean indicating test success
    """
    logger.info(f"Running specific tests: {', '.join(test_names)}")
    
    # Create a test suite for the specified tests
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    
    for test_name in test_names:
        try:
            if '.' in test_name:
                class_name, method_name = test_name.split('.')
                # Find the test class
                test_class = None
                for case in get_all_test_cases():
                    if case.__name__ == class_name:
                        test_class = case
                        break
                
                if not test_class:
                    logger.error(f"Test class {class_name} not found")
                    continue
                
                # Add the specific test method
                suite.addTest(loader.loadTestsFromName(method_name, test_class))
            else:
                # Assume it's a class name
                found = False
                for case in get_all_test_cases():
                    if case.__name__ == test_name:
                        suite.addTest(loader.loadTestsFromTestCase(case))
                        found = True
                        break
                
                if not found:
                    logger.error(f"Test class {test_name} not found")
        except Exception as e:
            logger.error(f"Error loading test {test_name}: {e}")
    
    # Run the suite
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def list_available_tests() -> None:
    """List all available tests in a user-friendly format."""
    print("\nAvailable Scenario Tests:")
    print("=" * 50)
    
    for test_class in get_all_test_cases():
        print(f"\n{test_class.__name__}")
        print("-" * len(test_class.__name__))
        
        # Get all test methods
        for name in dir(test_class):
            if name.startswith('test'):
                method = getattr(test_class, name)
                doc = method.__doc__ or "No description available"
                # Clean up doc string
                doc = doc.strip().split('\n')[0]
                print(f"  {name}: {doc}")
    
    print("\nTo run specific tests, use:")
    print("python -m tests.scenarios.standalone_test_runner --tests TestClass.test_method")
    print("=" * 50)

def main():
    """Main entry point for the standalone test runner."""
    parser = argparse.ArgumentParser(description="Run scenario-based tests")
    
    # Command line arguments
    parser.add_argument('--tests', nargs='+', help='Specific tests to run (format: TestClass.test_method)')
    parser.add_argument('--list', action='store_true', help='List all available tests')
    parser.add_argument('--verbose', '-v', action='count', default=1, help='Increase verbosity (use multiple times for more detail)')
    parser.add_argument('--quiet', '-q', action='store_true', help='Minimal output')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default='INFO', help='Set the logging level')
    
    args = parser.parse_args()
    
    # Set logging level
    logging_level = getattr(logging, args.log_level)
    logger.setLevel(logging_level)
    
    # Determine verbosity
    verbosity = 0 if args.quiet else args.verbose
    verbosity = min(verbosity, 3)  # Cap at 3
    
    # Action based on arguments
    if args.list:
        list_available_tests()
        return 0
    
    if args.tests:
        success = run_specific_tests(args.tests, verbosity)
    else:
        success = run_all_tests(verbosity)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 