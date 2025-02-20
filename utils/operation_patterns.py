"""Pattern matching for common menu operations"""
from typing import Dict, Optional, Any
import re

OPERATION_PATTERNS = {
    'price_update': {
        'patterns': [
            # Single item price updates
            r'(?i)update.*price.*(?:for|of)\s+(.+?)\s+to\s+(\d+\.?\d*)',
            r'(?i)change.*price.*(?:for|of)\s+(.+?)\s+to\s+(\d+\.?\d*)',
            r'(?i)set.*price.*(?:for|of)\s+(.+?)\s+to\s+(\d+\.?\d*)',
            # Bulk price updates
            r'(?i)update.*price.*(?:for|of)\s+(.+?)\s+everywhere\s+to\s+(\d+\.?\d*)',
            r'(?i)change.*price.*(?:for|of)\s+(.+?)\s+everywhere\s+to\s+(\d+\.?\d*)',
            # Option item price updates
            r'(?i)update.*price.*(?:for|of)\s+option\s+(.+?)\s+to\s+(\d+\.?\d*)',
            r'(?i)change.*price.*(?:for|of)\s+option\s+(.+?)\s+to\s+(\d+\.?\d*)',
        ],
        'operation': 'Price Updates',
        'extract_params': lambda match: {
            'item_name': match.group(1),
            'price': float(match.group(2)) if len(match.groups()) > 1 else None,
            'is_bulk': bool(re.search(r'everywhere', match.string)),
            'is_option': bool(re.search(r'option', match.string))
        }
    },
    'time_range': {
        'patterns': [
            r'(?i)set.*time.*(?:for|of)\s+(.+?)\s+to\s+(\d{4})-(\d{4})',
            r'(?i)update.*time.*(?:for|of)\s+(.+?)\s+to\s+(\d{4})-(\d{4})',
            r'(?i)change.*(?:hours|time).*(?:for|of)\s+(.+?)\s+to\s+(\d{4})-(\d{4})',
        ],
        'operation': 'Time Ranges',
        'extract_params': lambda match: {
            'category_name': match.group(1),
            'start_time': int(match.group(2)) if len(match.groups()) > 1 else None,
            'end_time': int(match.group(3)) if len(match.groups()) > 2 else None
        }
    },
    'enable_disable': {
        'patterns': [
            r'(?i)(enable|disable)\s+(.+)',
            r'(?i)(activate|deactivate)\s+(.+)',
            r'(?i)turn\s+(on|off)\s+(.+)',
        ],
        'operation': 'Enable/Disable',
        'extract_params': lambda match: {
            'action': match.group(1).lower(),
            'item_name': match.group(2)
        }
    },
    'copy_options': {
        'patterns': [
            r'(?i)copy.*options.*from\s+(.+)\s+to\s+(.+)',
            r'(?i)duplicate.*options.*from\s+(.+)\s+to\s+(.+)',
        ],
        'operation': 'Copy Options',
        'extract_params': lambda match: {
            'source_item': match.group(1),
            'target_item': match.group(2)
        }
    },
    'side_items': {
        'patterns': [
            r'(?i)update.*(?:list\s+of\s+)?side\s+items?\s+to\s+(.+)',
            r'(?i)change.*(?:list\s+of\s+)?side\s+items?\s+to\s+(.+)',
            r'(?i)set.*(?:list\s+of\s+)?side\s+items?\s+to\s+(.+)',
            r'(?i)add.*(?:list\s+of\s+)?side\s+items?\s+(.+)',
            r'(?i)replace.*(?:list\s+of\s+)?side\s+items?\s+with\s+(.+)',
        ],
        'operation': 'Side Items',
        'extract_params': lambda match: {
            'items': [item.strip() for item in match.group(1).split(',')],
            'operation_type': 'side_items',
            'is_bulk': True
        }
    }
}

def match_operation(query: str) -> Optional[Dict[str, Any]]:
    """Match query against operation patterns
    
    Args:
        query: User query string
        
    Returns:
        Dict with operation type, name and extracted parameters if matched,
        None otherwise
    """
    for op_type, config in OPERATION_PATTERNS.items():
        for pattern in config['patterns']:
            if match := re.match(pattern, query):
                return {
                    'type': op_type,
                    'operation': config['operation'],
                    'params': config['extract_params'](match)
                }
    return None
