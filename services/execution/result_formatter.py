"""
Result formatter for the Execution Service.

This module provides functionality for formatting database query results
into different formats suitable for display or further processing.
"""

import json
import csv
import io
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from decimal import Decimal
from datetime import datetime, date, time
import pandas as pd

# Get the logger that was configured in utils/logging.py
logger = logging.getLogger("swoop_ai")

def _json_serializer(obj: Any) -> str:
    """
    Custom JSON serializer for types that are not natively supported by json.
    
    Args:
        obj: Object to serialize
        
    Returns:
        String representation of the object
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, time):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif hasattr(obj, '__str__'):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")

def format_to_json(
    data: List[Dict[str, Any]], 
    pretty: bool = False
) -> str:
    """
    Format query results as JSON.
    
    Args:
        data: Query results as a list of dictionaries
        pretty: Whether to pretty-print the JSON (default: False)
        
    Returns:
        JSON string representation of the data
    """
    indent = 2 if pretty else None
    try:
        return json.dumps(data, default=_json_serializer, indent=indent)
    except Exception as e:
        logger.error(f"Error formatting results as JSON: {str(e)}")
        return json.dumps({"error": "Could not format results as JSON"})

def format_to_csv(
    data: List[Dict[str, Any]],
    include_header: bool = True
) -> str:
    """
    Format query results as CSV.
    
    Args:
        data: Query results as a list of dictionaries
        include_header: Whether to include header row (default: True)
        
    Returns:
        CSV string representation of the data
    """
    if not data:
        return ""
    
    output = io.StringIO()
    writer = None
    
    try:
        # Extract column names from the first row
        fieldnames = list(data[0].keys())
        
        # Create CSV writer
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        
        # Write header if requested
        if include_header:
            writer.writeheader()
        
        # Convert data types and write rows
        for row in data:
            # Convert special types to strings
            formatted_row = {}
            for key, value in row.items():
                if isinstance(value, (datetime, date, time, Decimal)):
                    formatted_row[key] = _json_serializer(value)
                else:
                    formatted_row[key] = value
            
            writer.writerow(formatted_row)
        
        return output.getvalue()
    except Exception as e:
        logger.error(f"Error formatting results as CSV: {str(e)}")
        return f"Error: {str(e)}"
    finally:
        output.close()

def format_to_dataframe(data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Format query results as a pandas DataFrame.
    
    Args:
        data: Query results as a list of dictionaries
        
    Returns:
        Pandas DataFrame
    """
    try:
        return pd.DataFrame(data)
    except Exception as e:
        logger.error(f"Error converting results to DataFrame: {str(e)}")
        return pd.DataFrame()

def format_to_text_table(
    data: List[Dict[str, Any]],
    max_col_width: int = 30
) -> str:
    """
    Format query results as a text table.
    
    Args:
        data: Query results as a list of dictionaries
        max_col_width: Maximum column width (default: 30)
        
    Returns:
        Text table representation of the data
    """
    if not data:
        return "No data"
    
    # Get column names from the first row
    columns = list(data[0].keys())
    
    # Calculate column widths (minimum width is the length of the column name)
    col_widths = {col: len(col) for col in columns}
    
    # Update column widths based on data
    for row in data:
        for col in columns:
            # Convert value to string and limit its length
            value_str = str(_json_serializer(row[col]) if row[col] is not None else "")
            if len(value_str) > max_col_width:
                value_str = value_str[:max_col_width-3] + "..."
            
            col_widths[col] = max(col_widths[col], len(value_str))
    
    # Create the table
    result = []
    
    # Add header row
    header = " | ".join(col.ljust(col_widths[col]) for col in columns)
    result.append(header)
    
    # Add separator
    separator = "-+-".join("-" * col_widths[col] for col in columns)
    result.append(separator)
    
    # Add data rows
    for row in data:
        values = []
        for col in columns:
            value = row[col]
            value_str = str(_json_serializer(value) if value is not None else "")
            if len(value_str) > max_col_width:
                value_str = value_str[:max_col_width-3] + "..."
            values.append(value_str.ljust(col_widths[col]))
        
        result.append(" | ".join(values))
    
    return "\n".join(result)

def format_result(
    data: List[Dict[str, Any]],
    format_type: str = "json",
    format_options: Optional[Dict[str, Any]] = None
) -> Union[str, pd.DataFrame]:
    """
    Format query results in the specified format.
    
    Args:
        data: Query results as a list of dictionaries
        format_type: Desired format ("json", "csv", "dataframe", "text")
        format_options: Format-specific options
        
    Returns:
        Formatted results
    """
    if not data:
        if format_type == "dataframe":
            return pd.DataFrame()
        return "" if format_type in ["json", "csv"] else "No data"
    
    options = format_options or {}
    
    if format_type == "json":
        pretty = options.get("pretty", False)
        return format_to_json(data, pretty=pretty)
    
    elif format_type == "csv":
        include_header = options.get("include_header", True)
        return format_to_csv(data, include_header=include_header)
    
    elif format_type == "dataframe":
        return format_to_dataframe(data)
    
    elif format_type == "text":
        max_col_width = options.get("max_col_width", 30)
        return format_to_text_table(data, max_col_width=max_col_width)
    
    else:
        logger.warning(f"Unsupported format type: {format_type}. Using JSON.")
        return format_to_json(data)

def get_summary_stats(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate summary statistics for query results.
    
    Args:
        data: Query results as a list of dictionaries
        
    Returns:
        Dictionary with summary statistics
    """
    if not data:
        return {
            "row_count": 0,
            "column_count": 0,
            "columns": []
        }
    
    # Get column names
    columns = list(data[0].keys())
    
    # Basic stats
    stats = {
        "row_count": len(data),
        "column_count": len(columns),
        "columns": columns
    }
    
    # Try to identify column types and compute basic statistics
    column_stats = {}
    
    for col in columns:
        values = [row[col] for row in data if row[col] is not None]
        non_null_count = len(values)
        null_count = len(data) - non_null_count
        
        col_stats = {
            "null_count": null_count,
            "non_null_count": non_null_count
        }
        
        # Check if all values are numeric
        if non_null_count > 0:
            try:
                numeric_values = [float(v) if v is not None else 0 for v in values]
                col_stats["min"] = min(numeric_values) if numeric_values else None
                col_stats["max"] = max(numeric_values) if numeric_values else None
                col_stats["avg"] = sum(numeric_values) / len(numeric_values) if numeric_values else None
                col_stats["type"] = "numeric"
            except (ValueError, TypeError):
                # Not all values are numeric
                col_stats["type"] = "text"
                if values:
                    col_stats["min_length"] = min(len(str(v)) for v in values)
                    col_stats["max_length"] = max(len(str(v)) for v in values)
        
        column_stats[col] = col_stats
    
    stats["column_stats"] = column_stats
    return stats 