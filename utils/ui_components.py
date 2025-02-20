"""UI components for menu operations with validation"""
import re
from typing import Dict, Any, List, Optional
import streamlit as st

def validate_menu_update(data: Dict[str, Any]) -> List[str]:
    """Validate menu updates in real-time"""
    errors = []
    
    # Price validation
    if 'price' in data:
        try:
            price = float(data['price'])
            if price < 0:
                errors.append("Price must be non-negative")
            if price > 500:
                errors.append("Price cannot exceed $500.00")
            if len(str(price).split('.')[-1]) > 2:
                errors.append("Price cannot have more than 2 decimal places")
        except ValueError:
            errors.append("Invalid price format")
    
    # Time range validation
    if 'start_time' in data or 'end_time' in data:
        for key in ['start_time', 'end_time']:
            if key in data and data[key]:
                time_str = str(data[key])
                if not re.match(r'^([01]\d|2[0-3])([0-5]\d)$', time_str):
                    errors.append(f"{key.replace('_', ' ').title()} must be in 24-hour format (0000-2359)")
    
    # Option limits validation
    if 'min_selections' in data and 'max_selections' in data:
        min_val = data['min_selections']
        max_val = data['max_selections']
        if min_val > max_val:
            errors.append("Minimum selections cannot exceed maximum")
        if max_val > 10:
            errors.append("Maximum selections cannot exceed 10")
        if min_val < 0:
            errors.append("Minimum selections cannot be negative")
    
    return errors

def render_price_input(label: str, key: str, default: float = 0.0) -> float:
    """Render price input with validation"""
    col1, col2 = st.columns([3, 1])
    with col1:
        price = st.number_input(
            label,
            min_value=0.0,
            max_value=500.0,
            value=default,
            step=0.01,
            key=key,
            help="Enter price (0.00 - 500.00)"
        )
    with col2:
        st.markdown("""
        <div class="tooltip" style="position:relative">
            ℹ️
            <span style="visibility:hidden;background-color:#555;color:#fff;text-align:center;
                        padding:5px;border-radius:6px;position:absolute;z-index:1;
                        bottom:125%;left:50%;margin-left:-60px;opacity:0;transition:opacity 0.3s">
                Price Rules:
                • Must be non-negative
                • Maximum $500.00
                • Two decimal places
            </span>
        </div>
        """, unsafe_allow_html=True)
    return price

def render_time_input(label: str, key: str, default: str = "") -> str:
    """Render time input with 24-hour format validation"""
    col1, col2 = st.columns([3, 1])
    with col1:
        time = st.text_input(
            label,
            value=default,
            key=key,
            help="Enter time in 24-hour format (0000-2359)"
        )
    with col2:
        st.markdown("""
        <div class="tooltip" style="position:relative">
            ℹ️
            <span style="visibility:hidden;background-color:#555;color:#fff;text-align:center;
                        padding:5px;border-radius:6px;position:absolute;z-index:1;
                        bottom:125%;left:50%;margin-left:-60px;opacity:0;transition:opacity 0.3s">
                Time Format:
                • 24-hour format (0000-2359)
                • Examples: 0900, 1430, 2200
            </span>
        </div>
        """, unsafe_allow_html=True)
    
    if time and not re.match(r'^([01]\d|2[0-3])([0-5]\d)$', time):
        st.error('Time must be in 24-hour format (0000-2359)')
    return time

def render_option_limits(min_label: str, max_label: str, key_prefix: str) -> tuple[int, int]:
    """Render min/max selection limits with validation"""
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        min_val = st.number_input(
            min_label,
            min_value=0,
            max_value=10,
            value=0,
            step=1,
            key=f"{key_prefix}_min"
        )
    
    with col2:
        max_val = st.number_input(
            max_label,
            min_value=min_val,
            max_value=10,
            value=max(min_val, 1),
            step=1,
            key=f"{key_prefix}_max"
        )
    
    with col3:
        st.markdown("""
        <div class="tooltip" style="position:relative">
            ℹ️
            <span style="visibility:hidden;background-color:#555;color:#fff;text-align:center;
                        padding:5px;border-radius:6px;position:absolute;z-index:1;
                        bottom:125%;left:50%;margin-left:-60px;opacity:0;transition:opacity 0.3s">
                Selection Limits:
                • Min: 0-10 items
                • Max: Must be ≥ Min
                • Used for option groups
            </span>
        </div>
        """, unsafe_allow_html=True)
    
    return min_val, max_val
