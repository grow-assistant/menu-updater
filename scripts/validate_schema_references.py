#!/usr/bin/env python
"""
Schema Reference Validator

This script validates database field references in files against the actual database schema.
It helps ensure that rules files use correct table and field names.
"""

import os
import sys
import argparse
from typing import List, Optional, Dict, Any

# Add the parent directory to the Python path so we can import the services package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.utils.schema_loader import SchemaLoader
from services.utils.schema_validator import SchemaValidator

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate database field references in files against the schema."
    )
    
    parser.add_argument(
        "path",
        help="Path to file or directory to validate"
    )
    
    parser.add_argument(
        "--schema",
        help="Path to schema YAML file (defaults to resources/schema.yaml)",
        default=None
    )
    
    parser.add_argument(
        "--extension",
        help="File extension to filter by when validating a directory (e.g., .py, .yml)",
        default=None
    )
    
    parser.add_argument(
        "--summary",
        help="Show only a summary of validation results",
        action="store_true"
    )
    
    return parser.parse_args()

def format_file_results(file_path: str, results: Dict[str, Any], summary: bool = False) -> List[str]:
    """Format validation results for a file."""
    output = []
    
    if 'error' in results:
        output.append(f"Error processing {file_path}: {results['error']}")
        return output
    
    if results['is_valid']:
        output.append(f"✓ {file_path}: VALID")
        return output
    
    output.append(f"✗ {file_path}: INVALID")
    
    if not summary:
        invalid_refs = results['invalid_references']
        
        if isinstance(invalid_refs, dict):
            for location, refs in invalid_refs.items():
                refs_str = ", ".join(sorted(refs))
                output.append(f"  - {location}: {refs_str}")
    
    return output

def main() -> int:
    """Main function."""
    args = parse_args()
    
    # Create schema loader and validator
    schema_loader = SchemaLoader(args.schema)
    validator = SchemaValidator(schema_loader)
    
    # Check if the path exists
    if not os.path.exists(args.path):
        print(f"Error: Path does not exist: {args.path}")
        return 1
    
    # Validate file or directory
    if os.path.isfile(args.path):
        if args.path.endswith(('.yml', '.yaml')):
            is_valid, invalid_refs = validator.validate_yaml_file(args.path)
        elif args.path.endswith('.py'):
            is_valid, invalid_refs = validator.validate_python_file(args.path)
        else:
            print(f"Error: Unsupported file type: {args.path}")
            return 1
        
        results = {
            'is_valid': is_valid,
            'invalid_references': invalid_refs
        }
        
        for line in format_file_results(args.path, results, args.summary):
            print(line)
        
        return 0 if is_valid else 1
    
    # Validate directory
    results = validator.validate_directory(args.path, args.extension)
    
    valid_count = sum(1 for r in results.values() if r.get('is_valid', False))
    invalid_count = len(results) - valid_count
    
    print(f"Validation Summary: {valid_count} valid, {invalid_count} invalid")
    
    # Print detailed results
    for file_path, file_results in sorted(results.items()):
        for line in format_file_results(file_path, file_results, args.summary):
            print(line)
    
    return 0 if invalid_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main()) 