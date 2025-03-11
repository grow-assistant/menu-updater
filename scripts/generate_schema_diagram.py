#!/usr/bin/env python3
"""
Generate database schema diagram from schema.yaml.

This script reads the schema.yaml file and generates a visualization of
table relationships as a DOT file that can be rendered with Graphviz.

Usage:
    python scripts/generate_schema_diagram.py [--output output.dot]
"""

import os
import sys
import yaml
import argparse
from typing import Dict, Any

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate database schema diagram from schema.yaml")
    parser.add_argument("--output", default="schema_diagram.dot",
                        help="Output DOT file path (default: schema_diagram.dot)")
    parser.add_argument("--schema", default="resources/schema.yaml",
                        help="Path to schema.yaml file (default: resources/schema.yaml)")
    return parser.parse_args()

def load_schema(schema_path: str) -> Dict[str, Any]:
    """Load schema from YAML file."""
    try:
        with open(schema_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"Error loading schema file {schema_path}: {str(e)}", file=sys.stderr)
        sys.exit(1)

def generate_dot_file(schema: Dict[str, Any], output_path: str) -> None:
    """Generate DOT file for the database schema."""
    tables = schema.get('tables', {})
    
    # Start DOT file
    with open(output_path, 'w') as file:
        file.write('digraph DatabaseSchema {\n')
        file.write('  rankdir=LR;\n')  # Left to right layout
        file.write('  node [shape=record, fontname="Arial", fontsize=10];\n')
        file.write('  edge [fontname="Arial", fontsize=8];\n\n')
        
        # Generate nodes for tables
        for table_name, table_info in tables.items():
            fields = table_info.get('fields', {})
            
            # Build table label with fields
            label = f"{table_name} | "
            field_records = []
            
            # Add fields with their types
            for field_name, field_info in fields.items():
                field_type = field_info.get('type', 'unknown')
                nullable = "" if field_info.get('nullable', True) else " NOT NULL"
                pk = " (PK)" if 'primary' in field_name.lower() or (field_name == 'id' and 'seq' in field_info.get('default', '')) else ""
                fk = " (FK)" if 'references' in field_info else ""
                field_records.append(f"{field_name}: {field_type}{nullable}{pk}{fk}")
            
            label += "\\l".join(field_records) + "\\l"
            
            # Write node definition
            file.write(f'  "{table_name}" [label="{{{label}}}"];\n')
        
        file.write('\n')
        
        # Generate edges for relationships
        for table_name, table_info in tables.items():
            fields = table_info.get('fields', {})
            
            for field_name, field_info in fields.items():
                if 'references' in field_info:
                    referenced = field_info['references']
                    # Parse the referenced table and field
                    ref_parts = referenced.split('.')
                    if len(ref_parts) == 2:
                        ref_table, ref_field = ref_parts
                        file.write(f'  "{table_name}" -> "{ref_table}" [label="{field_name} -> {ref_field}"];\n')
        
        file.write('}\n')
    
    print(f"Schema diagram generated at {output_path}")
    print("To convert to an image, use GraphViz:")
    print(f"  dot -Tpng {output_path} -o schema_diagram.png")

def main() -> int:
    """Main entry point."""
    args = parse_args()
    schema = load_schema(args.schema)
    generate_dot_file(schema, args.output)
    return 0

if __name__ == "__main__":
    sys.exit(main()) 