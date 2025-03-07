"""
Template Extractor Utility

This module provides utilities for extracting prompt templates from Python files
and converting them to standalone template files with proper variable placeholders.
"""

import re
import ast
import os
import importlib.util
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set

from services.utils.conversion_utils import import_module_from_file
from services.utils.logging import get_logger

logger = get_logger(__name__)


def extract_string_templates(py_file: str) -> Dict[str, str]:
    """
    Extract string templates from a Python file.
    
    Args:
        py_file: Path to Python file containing string templates
        
    Returns:
        Dictionary mapping template names to string content
    """
    templates = {}
    
    try:
        # Parse the Python file
        with open(py_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        # Find string assignments (e.g., TEMPLATE = "...")
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and isinstance(node.value, ast.Str):
                        templates[target.id] = node.value.s
                    elif isinstance(target, ast.Name) and isinstance(node.value, (ast.JoinedStr, ast.BinOp)):
                        # Extract f-strings or multi-line strings (''' or """)
                        try:
                            # Try to compile and execute just this assignment
                            compiled_code = compile(
                                ast.Module(body=[node], type_ignores=[]), 
                                filename="<ast>", 
                                mode="exec"
                            )
                            local_vars = {}
                            exec(compiled_code, {}, local_vars)
                            templates[target.id] = local_vars[target.id]
                        except Exception as e:
                            logger.warning(f"Could not extract template {target.id}: {e}")
        
        # Also look for triple-quoted strings
        triple_quote_pattern = r'([A-Z][A-Z_0-9]*)\s*=\s*"""(.*?)"""'
        for match in re.finditer(triple_quote_pattern, content, re.DOTALL):
            templates[match.group(1)] = match.group(2)
            
        # Also look for triple single-quoted strings
        triple_single_quote_pattern = r"([A-Z][A-Z_0-9]*)\s*=\s*'''(.*?)'''"
        for match in re.finditer(triple_single_quote_pattern, content, re.DOTALL):
            templates[match.group(1)] = match.group(2)
        
        return templates
    
    except Exception as e:
        logger.error(f"Error extracting string templates from {py_file}: {e}")
        return {}


def identify_template_variables(template: str) -> Set[str]:
    """
    Identify potential variables in a template string.
    
    Args:
        template: Template string to analyze
        
    Returns:
        Set of identified variable names
    """
    variables = set()
    
    # Look for {variable} patterns (standard Python format strings)
    format_vars = re.findall(r'\{([^{}]*?)\}', template)
    for var in format_vars:
        # Remove any format specifiers
        clean_var = var.split(':')[0].split('.')[0]
        if clean_var:
            variables.add(clean_var)
    
    # Look for $variable patterns (common in some templates)
    dollar_vars = re.findall(r'\$([a-zA-Z_][a-zA-Z0-9_]*)', template)
    variables.update(dollar_vars)
    
    # Look for [VARIABLE] patterns (common in SQL templates)
    bracket_vars = re.findall(r'\[([A-Z_][A-Z0-9_]*)\]', template)
    variables.update(map(str.lower, bracket_vars))
    
    return variables


def extract_builder_function(py_file: str) -> Optional[Tuple[str, Dict]]:
    """
    Extract a template builder function from a Python file.
    
    Args:
        py_file: Path to Python file containing a builder function
        
    Returns:
        Tuple of (function_name, parameter_dict) or None if not found
    """
    try:
        # Import the module
        module = import_module_from_file(py_file)
        
        # Look for builder functions
        for name in dir(module):
            if name.lower().startswith(('build', 'create', 'generate')) and name.lower().endswith(('prompt', 'template')):
                # Check if it's a function
                func = getattr(module, name)
                if callable(func):
                    # Get function signature
                    import inspect
                    sig = inspect.signature(func)
                    params = {
                        param_name: param.default if param.default is not inspect.Parameter.empty else None
                        for param_name, param in sig.parameters.items()
                        if param_name != 'self'  # Skip 'self' parameter for methods
                    }
                    return name, params
        
        return None
    
    except Exception as e:
        logger.error(f"Error extracting builder function from {py_file}: {e}")
        return None


def create_template_from_prompt_file(
    py_file: str, 
    template_file: str,
    template_var_name: Optional[str] = None,
    variable_format: str = "${{{}}}"
) -> bool:
    """
    Create a template file from a Python prompt file.
    
    Args:
        py_file: Path to Python file containing the prompt template
        template_file: Path where the template file should be written
        template_var_name: Optional name of the template variable to extract
        variable_format: Format string for template variables
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        template_path = Path(template_file)
        template_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Extract templates from the file
        templates = extract_string_templates(py_file)
        if not templates:
            logger.warning(f"No templates found in {py_file}")
            return False
        
        # If no specific template was requested, use the first one with "TEMPLATE" in the name
        if template_var_name is None:
            template_candidates = [
                name for name in templates.keys() 
                if "TEMPLATE" in name or "PROMPT" in name
            ]
            if template_candidates:
                template_var_name = template_candidates[0]
            else:
                template_var_name = list(templates.keys())[0]
        
        # Get the template content
        if template_var_name not in templates:
            logger.warning(f"Template {template_var_name} not found in {py_file}")
            return False
        
        template_content = templates[template_var_name]
        
        # Extract builder function info
        builder_info = extract_builder_function(py_file)
        if builder_info:
            function_name, params = builder_info
            
            # Replace placeholders with template variables
            for param_name in params:
                if param_name != 'self' and param_name != 'query' and param_name != 'cached_dates':
                    # Look for {param_name} in the template
                    template_content = re.sub(
                        r'\{' + param_name + r'(?:[^}]*)\}',
                        variable_format.format(param_name),
                        template_content
                    )
        
        # Identify potential variables in the template
        variables = identify_template_variables(template_content)
        
        # Add a commented section at the top with identified variables
        if variables:
            variable_comment = "# Template Variables:\n"
            for var in sorted(variables):
                variable_comment += f"# - {var}: [Description of {var}]\n"
            template_content = variable_comment + "\n" + template_content
        
        # Write the template to file
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write(template_content)
        
        logger.info(f"Created template file: {template_file}")
        return True
    
    except Exception as e:
        logger.error(f"Error creating template from {py_file}: {e}")
        return False


def batch_extract_templates(source_dir: str, target_dir: str, template_mapping: Dict[str, str]) -> Dict[str, bool]:
    """
    Extract templates from multiple Python files.
    
    Args:
        source_dir: Source directory containing Python files
        target_dir: Target directory for template files
        template_mapping: Dictionary mapping source file patterns to target file patterns
        
    Returns:
        Dictionary mapping source files to success status
    """
    results = {}
    
    # Iterate through the template mapping
    for source_pattern, target_pattern in template_mapping.items():
        # Find matching files in the source directory
        source_path = Path(source_dir)
        matching_files = list(source_path.glob(source_pattern))
        
        for source_file in matching_files:
            # Determine target file path
            rel_path = source_file.relative_to(source_path)
            target_file = Path(target_dir) / target_pattern.format(stem=rel_path.stem)
            
            # Extract the template
            success = create_template_from_prompt_file(str(source_file), str(target_file))
            results[str(source_file)] = success
    
    return results 