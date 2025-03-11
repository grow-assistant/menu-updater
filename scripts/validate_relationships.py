#!/usr/bin/env python3
"""
Validate relationship declarations in rule files.

This script validates that all relationship declarations in rule files match
the actual database schema definition.

Usage:
    python scripts/validate_relationships.py [--directory services/rules] [--extension .py]
"""

import os
import sys
import argparse
import json
from typing import Dict, Any, List

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from services.utils.relationship_validator import RelationshipValidator

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate relationship declarations in rule files"
    )
    parser.add_argument(
        "--directory",
        default="services/rules",
        help="Directory containing rule files to validate (default: services/rules)"
    )
    parser.add_argument(
        "--extension",
        help="Filter files by extension (e.g., .py, .yml)"
    )
    parser.add_argument(
        "--output",
        help="Path to output file for JSON results (optional)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed error messages"
    )
    return parser.parse_args()

def format_results(results: Dict[str, Dict[str, Any]], verbose: bool = False) -> List[str]:
    """Format validation results for display."""
    output = []
    valid_count = sum(1 for r in results.values() if r["is_valid"])
    invalid_count = len(results) - valid_count
    
    output.append(f"Validation Summary: {valid_count} valid, {invalid_count} invalid")
    output.append("")
    
    if invalid_count > 0:
        output.append("Invalid files:")
        for file_path, result in sorted(results.items()):
            if not result["is_valid"]:
                rel_path = os.path.relpath(file_path)
                output.append(f"  - {rel_path}")
                
                if verbose:
                    # Add detailed error messages
                    for key, errors in result.get("errors", {}).items():
                        if isinstance(errors, dict):
                            # Handle dictionary of errors
                            for category, messages in errors.items():
                                if isinstance(messages, list):
                                    for msg in messages:
                                        output.append(f"      • {key}.{category}: {msg}")
                                else:
                                    output.append(f"      • {key}.{category}: {messages}")
                        elif isinstance(errors, str):
                            # Handle string error messages
                            output.append(f"      • {key}: {errors}")
        
    return output

def main() -> int:
    """Main entry point."""
    args = parse_args()
    
    # Create validator and run validation
    validator = RelationshipValidator()
    results = validator.validate_directory(args.directory, args.extension)
    
    # Format and display results
    output = format_results(results, args.verbose)
    for line in output:
        print(line)
    
    # Write results to file if requested
    if args.output:
        try:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nDetailed results written to {args.output}")
        except Exception as e:
            print(f"Error writing to output file: {str(e)}", file=sys.stderr)
            return 1
    
    # Return non-zero exit code if any files are invalid
    return 0 if all(r["is_valid"] for r in results.values()) else 1

if __name__ == "__main__":
    sys.exit(main()) 