# Database Schema Implementation Plan

This document outlines the plan to improve the integration between the database schema and the rules system, ensuring proper field references and validation.

## Tasks

### 1. Create a structured YAML/JSON version of database_fields.md

- [x] Convert the existing database_fields.md document into a structured YAML or JSON format
- [x] Define tables as top-level objects
- [x] For each table, define fields with their data types and constraints
- [x] Include relationships between tables (foreign keys)
- [x] Store the schema file in the resources directory
- [x] Create a schema loader utility to programmatically access the schema

### 2. Update rules files to reference the correct field names

- [x] Audit all rules files for database field references
- [x] Update rules files (both YML and Python) to use the correct field names from the schema
- [x] Implement a field name validation helper to verify field names against the schema
- [x] Create automated tests to verify field references in rules are valid

### 3. Add schema validation to SQL generation process

- [x] Implement pre-generation validation to check field names in queries
- [x] Add table existence validation before generating SQL
- [x] Verify relationship integrity when joining tables
- [x] Add warnings or errors for mismatches between rules and schema
- [x] Create unit tests for the validation process

### 4. Document table relationships explicitly in rules

- [x] Add relationship declarations in the rules system
- [x] Update the rules format to support relationship metadata
- [x] Document primary key and foreign key relationships
- [x] Create visualization of table relationships for documentation
- [x] Update existing rules to include relationship information

## Implementation Progress

- Completed the schema.yaml file in resources directory with all tables and fields from database_fields.md
- Created SchemaLoader utility class with comprehensive methods to:
  - Validate field references against the schema
  - Check table existence
  - Get table fields and field information
  - Get foreign key relationships
  - Get referencing fields (reverse relationships)
- Implemented SchemaValidator class to validate field references in:
  - YAML files (including nested structures)
  - Python files (with line number detection)
  - Entire directories of files
- Added a CLI tool (scripts/validate_schema_references.py) to check files against the schema
- Fixed table alias issues in rule files:
  - Updated references from `o.location_id` to `orders.location_id`
  - Updated other field aliases to use proper table names (e.g., `oi.quantity` to `order_items.quantity`)
  - Made sure all rules consistently use full table names instead of aliases
- Enhanced relationship documentation in rules:
  - Added comprehensive relationship metadata to schema definitions
  - Added `primary_key`, `indexes`, and `referenced_by` fields
  - Made relationship declarations consistent across rule files
- Created utilities for schema relationship management:
  - Created `generate_schema_diagram.py` script to visualize table relationships
  - Created `RelationshipValidator` class to validate relationship declarations against the schema
  - Created `validate_relationships.py` script to check rule files
  - Added unit tests for testing the relationship validator

## Benefits Achieved

The changes made have ensured that the rules system properly reflects the actual database schema, helping to prevent query errors due to incorrect field or table references. By introducing schema validation early in the SQL generation process, we now catch potential issues before they cause runtime errors or incorrect data retrieval.

Key benefits include:
1. Consistent naming across all rule files prevents confusion
2. Full table names instead of aliases improves readability and maintainability
3. Explicit relationship documentation helps new developers understand table connections
4. Visualization tools help with understanding complex database relationships
5. Validation tools catch errors early in the development process

## Next Steps

1. **Run Schema Validator in CI/CD Pipeline**:
   - Integrate `validate_relationships.py` and `validate_schema_references.py` into CI/CD pipelines
   - Add pre-commit hooks to validate schema references before commits
   - Set up automated testing for relationship validation

2. **Enhance Relationship Validator**:
   - Improve Python file parsing to better handle complex rule files
   - Add support for validating join structures in rules
   - Create more comprehensive documentation of relationship validation rules

3. **Create Schema Documentation**:
   - Generate comprehensive schema documentation from schema.yaml
   - Include relationship diagrams in documentation
   - Add examples of proper join structures based on schema relationships

4. **Implement Schema-Aware SQL Generation**:
   - Use relationship information to suggest optimal join paths
   - Validate join conditions against schema relationships
   - Add autocomplete suggestions based on schema information 