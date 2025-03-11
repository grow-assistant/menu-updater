#!/usr/bin/env python
"""
Database Schema Reference Auditor

This script audits database field references in rules files and filters out
import/module references to focus on actual database field references.
"""

import os
import sys
import re
import argparse
import json
from typing import Dict, List, Set, Any, Union

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.utils.schema_loader import SchemaLoader
from services.utils.schema_validator import SchemaValidator

# Common patterns that are not actual database references
NON_DB_PATTERNS = [
    r'import\s+[\w\.]+',
    r'from\s+[\w\.]+\s+import',
    r'logging\.',
    r'sys\.',
    r'os\.',
    r'time\.',
    r'json\.',
    r'yaml\.',
    r'service\.',
    r'config\.',
    r'file\.',
    r'self\.',
    r'\w+\.items',
    r'\w+\.get',
    r'\w+\.append',
    r'\w+\.copy',
    r'\w+\.replace',
    r'\w+\.load',
    r'\w+\.read',
    r'e\.g',
    r'logger\.',
]

def is_likely_db_reference(text: str) -> bool:
    """
    Determine if a text is likely a database reference or just a code element.
    
    Args:
        text: Text to check
        
    Returns:
        True if likely a database reference, False otherwise
    """
    # Check if it matches any non-DB patterns
    for pattern in NON_DB_PATTERNS:
        if re.search(pattern, text):
            return False
            
    # Check if it matches common table.field pattern with common field names
    db_pattern = r'([a-z_]+)\.([a-z_]+)'
    match = re.search(db_pattern, text)
    if match:
        table, field = match.groups()
        common_db_fields = ['id', 'name', 'created_at', 'updated_at', 'deleted_at', 
                          'description', 'disabled', 'location_id', 'user_id', 
                          'status', 'type', 'price', 'total', 'customer_id']
        if field in common_db_fields:
            return True
            
    return False

def filter_validation_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter validation results to focus on likely database field references.
    
    Args:
        results: Validation results from SchemaValidator
        
    Returns:
        Filtered validation results
    """
    filtered_results = {}
    
    for file_path, file_results in results.items():
        if not file_results.get('is_valid', True) and 'invalid_references' in file_results:
            filtered_invalid_refs = {}
            
            for location, refs in file_results['invalid_references'].items():
                filtered_refs = set()
                for ref in refs:
                    # Only include likely database references
                    context = f"{location}: {ref}"
                    if is_likely_db_reference(context):
                        filtered_refs.add(ref)
                
                if filtered_refs:
                    filtered_invalid_refs[location] = filtered_refs
            
            if filtered_invalid_refs:
                filtered_results[file_path] = {
                    'is_valid': False,
                    'invalid_references': filtered_invalid_refs
                }
    
    return filtered_results

def audit_paths(paths: List[str], extension: str = None, output_file: str = None) -> int:
    """
    Audit a list of files or directories for database field references and output results.
    
    Args:
        paths: List of file or directory paths to audit
        extension: File extension to filter by for directories
        output_file: Optional file to write JSON results to
        
    Returns:
        Exit code (0 for success, 1 for errors)
    """
    schema_loader = SchemaLoader()
    validator = SchemaValidator(schema_loader)
    
    all_results = {}
    
    for path in paths:
        # Check if the path is a file or directory
        if os.path.isfile(path):
            # Validate a single file
            try:
                if path.endswith(('.yml', '.yaml')):
                    is_valid, invalid_refs = validator.validate_yaml_file(path)
                elif path.endswith('.py'):
                    is_valid, invalid_refs = validator.validate_python_file(path)
                else:
                    print(f"Skipping unsupported file type: {path}")
                    continue
                
                all_results[path] = {
                    'is_valid': is_valid,
                    'invalid_references': invalid_refs
                }
            except Exception as e:
                print(f"Error validating {path}: {str(e)}")
                
        elif os.path.isdir(path):
            # Validate a directory
            dir_results = validator.validate_directory(path, extension)
            all_results.update(dir_results)
        else:
            print(f"Path not found: {path}")
    
    # Filter results to focus on likely database references
    filtered_results = filter_validation_results(all_results)
    
    # Count valid and invalid files
    valid_count = len(all_results) - len(filtered_results)
    invalid_count = len(filtered_results)
    
    print(f"Audit Summary: {valid_count} valid, {invalid_count} invalid (after filtering)")
    
    # Print or write detailed results
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(filtered_results, f, indent=2, default=list)
        print(f"Detailed results written to {output_file}")
    else:
        for file_path, file_results in sorted(filtered_results.items()):
            print(f"✗ {file_path}")
            for location, refs in sorted(file_results['invalid_references'].items()):
                refs_str = ", ".join(sorted(refs))
                print(f"  - {location}: {refs_str}")
    
    return 0 if invalid_count == 0 else 1

def main() -> int:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Audit database field references in files."
    )
    
    parser.add_argument(
        "paths",
        nargs='+',
        help="Paths to files or directories to audit"
    )
    
    parser.add_argument(
        "--extension",
        help="File extension to filter by for directories (e.g., .py, .yml)",
        default=None
    )
    
    parser.add_argument(
        "--output",
        help="Output file for detailed results (JSON format)",
        default=None
    )
    
    args = parser.parse_args()
    
    return audit_paths(args.paths, args.extension, args.output)

if __name__ == "__main__":
    sys.exit(main()) 