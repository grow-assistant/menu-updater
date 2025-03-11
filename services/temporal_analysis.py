"""
Temporal Analysis Service for Swoop AI Conversational Query Flow.

This module provides functionality for extracting and resolving time references
from natural language queries, as specified in the SWOOP development plan.
"""
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta, date
import calendar
import re
import logging

logger = logging.getLogger(__name__)


class TemporalAnalysisService:
    """
    Extracts and resolves time references from natural language queries.
    Handles explicit dates, relative references, and ranges.
    """
    
    # Patterns for common time expressions
    RELATIVE_PATTERNS = {
        'yesterday': -1,  # days
        'last week': -7,  # days
        'previous week': -7,  # days
        'last month': (-1, 'month'),
        'previous month': (-1, 'month'),
        'last quarter': (-3, 'month'),
        'previous quarter': (-3, 'month'),
        'last year': (-1, 'year'),
        'previous year': (-1, 'year'),
        'this week': 0,  # current week
        'this month': (0, 'month'),  # current month
        'this quarter': (0, 'quarter'),  # current quarter
        'this year': (0, 'year'),  # current year
        'recent': -7,  # days
        'recently': -7,  # days
        
        # Adding more relative patterns for enhanced coverage
        'last few days': -3,  # days
        'past week': -7,  # days
        'past month': (-1, 'month'),
        'past quarter': (-3, 'month'),
        'past year': (-1, 'year'),
        'previous 7 days': -7,  # days
        'previous 30 days': -30,  # days
        'previous 90 days': -90,  # days
        'ytd': ('year_to_date',),  # special case for year-to-date
        'year to date': ('year_to_date',),
        'mtd': ('month_to_date',),  # special case for month-to-date
        'month to date': ('month_to_date',),
        'qtd': ('quarter_to_date',),  # special case for quarter-to-date
        'quarter to date': ('quarter_to_date',),
        'today': 0,  # days
        'current day': 0,  # days
        'current week': 0,  # current week
        'current month': (0, 'month'),  # current month
        'current quarter': (0, 'quarter'),  # current quarter
        'current year': (0, 'year')  # current year
    }
    
    # Comparative time periods for trend analysis
    COMPARATIVE_PATTERNS = {
        'compared to': 'compare',
        'compared with': 'compare',
        'versus': 'compare',
        'vs': 'compare',
        'against': 'compare',
        'relative to': 'compare',
        'year over year': 'yoy',
        'yoy': 'yoy',
        'month over month': 'mom',
        'mom': 'mom',
        'quarter over quarter': 'qoq',
        'qoq': 'qoq',
        'week over week': 'wow',
        'wow': 'wow',
        'same period last year': 'yoy',
        'same period last month': 'mom',
        'same period last quarter': 'qoq',
        'same period last week': 'wow'
    }
    
    MONTH_PATTERNS = {
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2,
        'march': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'may': 5,
        'june': 6, 'jun': 6,
        'july': 7, 'jul': 7,
        'august': 8, 'aug': 8,
        'september': 9, 'sep': 9, 'sept': 9,
        'october': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12
    }
    
    # Regex patterns for matching in text
    REGEX_PATTERNS = {
        r'yesterday': 'yesterday',
        r'last\s+week': 'last week',
        r'previous\s+week': 'previous week',
        r'last\s+month': 'last month',
        r'previous\s+month': 'previous month',
        r'last\s+quarter': 'last quarter',
        r'previous\s+quarter': 'previous quarter',
        r'last\s+year': 'last year',
        r'previous\s+year': 'previous year',
        r'this\s+week': 'this week',
        r'this\s+month': 'this month',
        r'this\s+quarter': 'this quarter',
        r'this\s+year': 'this year',
        r'recent(ly)?': 'recent',
        
        # New patterns
        r'last\s+few\s+days': 'last few days',
        r'past\s+week': 'past week',
        r'past\s+month': 'past month',
        r'past\s+quarter': 'past quarter',
        r'past\s+year': 'past year',
        r'previous\s+7\s+days': 'previous 7 days',
        r'previous\s+30\s+days': 'previous 30 days',
        r'previous\s+90\s+days': 'previous 90 days',
        r'year\s+to\s+date': 'year to date',
        r'month\s+to\s+date': 'month to date',
        r'quarter\s+to\s+date': 'quarter to date',
        r'ytd': 'ytd',
        r'mtd': 'mtd',
        r'qtd': 'qtd',
        r'today': 'today',
        r'current\s+day': 'current day',
        r'current\s+week': 'current week',
        r'current\s+month': 'current month',
        r'current\s+quarter': 'current quarter',
        r'current\s+year': 'current year'
    }
    
    # Patterns for date ranges
    DATE_RANGE_PATTERNS = [
        r'(from|between)\s+(.+?)\s+(to|and|until|through)\s+(.+?)(?=\s|$|\.|\,)',
        r'(.+?)\s+(to|through|until)\s+(.+?)(?=\s|$|\.|\,)'
    ]
    
    # Enhanced date formats for parsing explicit dates
    DATE_FORMATS = [
        r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})',  # MM/DD/YYYY or DD/MM/YYYY
        r'(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})',  # YYYY/MM/DD
        r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s\.,-]+(\d{1,2})(?:st|nd|rd|th)?[\s\.,-]+(\d{2,4})',  # Month DD, YYYY
        r'(\d{1,2})(?:st|nd|rd|th)?[\s\.,-]+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s\.,-]+(\d{2,4})',  # DD Month, YYYY
        r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s\.,-]+(\d{4})'  # Month YYYY
        # Quarter formats removed from here as they're handled separately
    ]
    
    def __init__(self):
        """Initialize the temporal analysis service."""
        logger.info("Initialized TemporalAnalysisService")
    
    def analyze(self, query_text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Extract and resolve time references from a query.
        
        Args:
            query_text: User's query text
            context: Optional conversation context with previous time references
            
        Returns:
            Dict containing:
                - explicit_dates: List of specific dates mentioned
                - relative_references: List of relative time references ("last month", etc.)
                - resolved_time_period: Dict with start_date and end_date
                - is_ambiguous: Whether the time reference is ambiguous
                - needs_clarification: Whether time clarification is needed
                - clarification_question: Suggested question if clarification is needed
                - comparative_analysis: Information about trend comparison requests
        """
        result = {
            'explicit_dates': [],
            'relative_references': [],
            'resolved_time_period': None,
            'is_ambiguous': False,
            'needs_clarification': False,
            'clarification_question': None,
            'comparative_analysis': None
        }
        
        # Clean and normalize the query text
        cleaned_text = query_text.lower().strip()
        
        # Extract explicit dates
        explicit_dates = self._extract_explicit_dates(cleaned_text)
        if explicit_dates:
            result['explicit_dates'] = explicit_dates
        
        # Extract date ranges
        date_range = self._extract_date_range(cleaned_text)
        
        # Extract relative references
        relative_refs = self._extract_relative_references(cleaned_text)
        if relative_refs:
            result['relative_references'] = relative_refs
        
        # Extract comparative analysis requests
        comparative = self._extract_comparative_analysis(cleaned_text)
        if comparative:
            result['comparative_analysis'] = comparative
        
        # Determine if we have time references
        has_time_refs = explicit_dates or relative_refs or date_range
        
        # If no time references in query but we have context, use context
        if not has_time_refs and context and 'time_references' in context:
            ctx_time_refs = context['time_references']
            if ctx_time_refs.get('resolved_time_period'):
                result['resolved_time_period'] = ctx_time_refs['resolved_time_period']
                return result
        
        # If no time references at all, mark as needing clarification
        if not has_time_refs and not (context and 'time_references' in context and context['time_references'].get('resolved_time_period')):
            result['is_ambiguous'] = True
            result['needs_clarification'] = True
            result['clarification_question'] = "For what time period would you like to see this information?"
            return result
        
        # Resolve the time references to a specific period
        if date_range:
            result['resolved_time_period'] = date_range
        elif explicit_dates:
            # If we have a single date, use it as both start and end
            if len(explicit_dates) == 1:
                date_obj = explicit_dates[0]
                result['resolved_time_period'] = {
                    'start_date': date_obj,
                    'end_date': date_obj
                }
            # If we have multiple dates, use the first and last
            elif len(explicit_dates) > 1:
                explicit_dates.sort()
                result['resolved_time_period'] = {
                    'start_date': explicit_dates[0],
                    'end_date': explicit_dates[-1]
                }
        elif relative_refs:
            # Resolve each relative reference and use the most specific one
            resolved_periods = [self.resolve_relative_reference(ref) for ref in relative_refs]
            # Use the most specific (shortest) time period
            if resolved_periods:
                # Sort by duration (end - start)
                sorted_periods = sorted(
                    resolved_periods,
                    key=lambda p: (p['end_date'] - p['start_date']).total_seconds()
                )
                result['resolved_time_period'] = sorted_periods[0]
        
        # Add comparison period if needed
        if result['comparative_analysis'] and result['resolved_time_period']:
            result['comparative_analysis']['comparison_period'] = self._calculate_comparison_period(
                result['resolved_time_period'],
                result['comparative_analysis']['type']
            )
        
        return result
    
    def _extract_explicit_dates(self, text: str) -> List[datetime]:
        """
        Extract explicit date mentions from text.
        
        Args:
            text: The text to analyze
            
        Returns:
            List of datetime objects for each explicit date found
        """
        dates = []
        
        # Current year for default
        current_year = datetime.now().year
        
        # Simple month-year pattern for better detection
        month_year_pattern = r'(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\s+(\d{4})'
        for match in re.finditer(month_year_pattern, text, re.IGNORECASE):
            month_name, year_str = match.groups()
            month_num = self.MONTH_PATTERNS.get(month_name.lower())
            if month_num:
                year = int(year_str)
                # Create date for first day of month
                try:
                    date_obj = datetime(year, month_num, 1)
                    dates.append(date_obj)
                except ValueError:
                    logger.warning(f"Invalid date: {month_name} {year}")
        
        # Process quarter patterns separately
        quarter_pattern = r'q(\d)\s+(\d{4})'
        found_quarters = set()  # To detect and prevent duplicates
        
        for match in re.finditer(quarter_pattern, text, re.IGNORECASE):
            quarter, year = match.groups()
            quarter, year = int(quarter), int(year)
            
            # Skip if already processed
            quarter_key = f"Q{quarter}-{year}"
            if quarter_key in found_quarters:
                continue
            
            found_quarters.add(quarter_key)
            
            # Convert quarter to month (Q1=1, Q2=4, Q3=7, Q4=10)
            month = 1 + (quarter-1) * 3
            
            # Create date for first day of quarter
            try:
                date_obj = datetime(year, month, 1)
                dates.append(date_obj)
            except ValueError:
                logger.warning(f"Invalid quarter: Q{quarter} {year}")
        
        # The reverse pattern (2023 Q1)
        reverse_quarter_pattern = r'(\d{4})\s+q(\d)'
        for match in re.finditer(reverse_quarter_pattern, text, re.IGNORECASE):
            year, quarter = match.groups()
            year, quarter = int(year), int(quarter)
            
            # Skip if already processed
            quarter_key = f"Q{quarter}-{year}"
            if quarter_key in found_quarters:
                continue
            
            found_quarters.add(quarter_key)
            
            # Convert quarter to month (Q1=1, Q2=4, Q3=7, Q4=10)
            month = 1 + (quarter-1) * 3
            
            # Create date for first day of quarter
            try:
                date_obj = datetime(year, month, 1)
                dates.append(date_obj)
            except ValueError:
                logger.warning(f"Invalid quarter: Q{quarter} {year}")
        
        # Extract dates using the defined formats
        for pattern in self.DATE_FORMATS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    # Handle different formats
                    if pattern == r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})':
                        month, day, year = match.groups()
                        month, day = int(month), int(day)
                        year = int(year)
                        if year < 100:
                            year += 2000 if year < 50 else 1900
                        
                        # Handle potential day/month confusion based on values
                        if month > 12:
                            month, day = day, month
                        
                        dates.append(datetime(year, month, day))
                    
                    elif pattern == r'(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})':
                        year, month, day = match.groups()
                        year, month, day = int(year), int(month), int(day)
                        dates.append(datetime(year, month, day))
                    
                    elif pattern.startswith(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)'):
                        month_str, day, year = match.groups()
                        month = self.MONTH_PATTERNS.get(month_str.lower(), 1)
                        day, year = int(day), int(year)
                        if year < 100:
                            year += 2000 if year < 50 else 1900
                        dates.append(datetime(year, month, day))
                    
                    elif pattern.startswith(r'(\d{1,2})(?:st|nd|rd|th)?'):
                        day, month_str, year = match.groups()
                        month = self.MONTH_PATTERNS.get(month_str.lower(), 1)
                        day, year = int(day), int(year)
                        if year < 100:
                            year += 2000 if year < 50 else 1900
                        dates.append(datetime(year, month, day))
                    
                    elif pattern.endswith(r'(\d{4})'):
                        month_str, year = match.groups()
                        month = self.MONTH_PATTERNS.get(month_str.lower(), 1)
                        year = int(year)
                        if year < 100:
                            year += 2000 if year < 50 else 1900
                        # Use the first day of the month
                        dates.append(datetime(year, month, 1))
                
                except (ValueError, KeyError) as e:
                    logger.debug(f"Error parsing date: {e}")
                    continue
        
        return dates
    
    def _extract_relative_references(self, text: str) -> List[str]:
        """
        Extract relative time references from text.
        
        Args:
            text: The text to analyze
            
        Returns:
            List of relative reference strings
        """
        references = []
        
        for pattern, key in self.REGEX_PATTERNS.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if key not in references:
                    references.append(key)
        
        return references
    
    def _extract_date_range(self, text: str) -> Optional[Dict[str, datetime]]:
        """
        Extract date range mentions from text.
        
        Args:
            text: The text to analyze
            
        Returns:
            Dict with start_date and end_date, or None if no range found
        """
        for pattern in self.DATE_RANGE_PATTERNS:
            matches = re.search(pattern, text, re.IGNORECASE)
            if matches:
                # Handle "from X to Y" format
                if len(matches.groups()) == 4:
                    _, start_text, _, end_text = matches.groups()
                # Handle "X to Y" format
                else:
                    start_text, _, end_text = matches.groups()
                
                # Try to get start and end dates
                start_date = None
                end_date = None
                
                # Try explicit dates first
                start_explicit_dates = self._extract_explicit_dates(start_text)
                if start_explicit_dates:
                    start_date = start_explicit_dates[0]
                
                end_explicit_dates = self._extract_explicit_dates(end_text)
                if end_explicit_dates:
                    end_date = end_explicit_dates[0]
                
                # If explicit dates not found, try relative references
                if not start_date:
                    # Try to find a relative reference in the start text
                    for key in self.RELATIVE_PATTERNS.keys():
                        if key in start_text.lower():
                            period = self.resolve_relative_reference(key)
                            start_date = period['start_date']
                            # If no explicit end date, use the end date from this period
                            if not end_date and 'last month' in start_text.lower():
                                end_date = period['end_date']
                            break
                
                if not end_date:
                    # Try to find a relative reference in the end text
                    for key in self.RELATIVE_PATTERNS.keys():
                        if key in end_text.lower():
                            period = self.resolve_relative_reference(key)
                            end_date = period['end_date']
                            break
                
                # If we have both dates, return the range
                if start_date and end_date:
                    return {
                        'start_date': start_date,
                        'end_date': end_date
                    }
        
        return None
    
    def _extract_comparative_analysis(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract requests for comparative analysis.
        
        Args:
            text: The text to analyze
            
        Returns:
            Dict with comparison type and parameters, or None if not found
        """
        for phrase, comp_type in self.COMPARATIVE_PATTERNS.items():
            if phrase in text:
                return {
                    'type': comp_type,
                    'comparison_period': None  # Will be filled in later
                }
        
        return None
    
    def resolve_relative_reference(self, reference: str, base_date: Optional[datetime] = None) -> Dict[str, datetime]:
        """
        Convert a relative time reference to an absolute time period.
        
        Args:
            reference: Relative reference string (e.g., "last month")
            base_date: Optional base date (defaults to today)
            
        Returns:
            Dict with start_date and end_date
        """
        if not base_date:
            base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Handle special cases first
        if reference == 'today' or reference == 'current day':
            return {
                'start_date': base_date,
                'end_date': base_date
            }
        
        # Get the time shift value
        shift = self.RELATIVE_PATTERNS.get(reference)
        
        # Handle different types of shifts
        if isinstance(shift, int):
            # Simple day shift
            if shift == 0:
                # For "this week", "this month", etc.
                if 'week' in reference:
                    # Get the first day of the current week (Monday)
                    start_date = base_date - timedelta(days=base_date.weekday())
                    # Get the last day of the current week (Sunday)
                    end_date = start_date + timedelta(days=6)
                elif 'month' in reference:
                    # Get the first day of the current month
                    start_date = base_date.replace(day=1)
                    # Get the last day of the current month
                    last_day = calendar.monthrange(start_date.year, start_date.month)[1]
                    end_date = start_date.replace(day=last_day)
                elif 'quarter' in reference:
                    # Determine the current quarter
                    quarter = (base_date.month - 1) // 3 + 1
                    # Get the first day of the current quarter
                    start_month = (quarter - 1) * 3 + 1
                    start_date = base_date.replace(month=start_month, day=1)
                    # Get the last day of the current quarter
                    if quarter == 4:
                        end_date = base_date.replace(month=12, day=31)
                    else:
                        end_month = quarter * 3
                        last_day = calendar.monthrange(base_date.year, end_month)[1]
                        end_date = base_date.replace(month=end_month, day=last_day)
                elif 'year' in reference:
                    # Get the first day of the current year
                    start_date = base_date.replace(month=1, day=1)
                    # Get the last day of the current year
                    end_date = base_date.replace(month=12, day=31)
                else:
                    # Default to today
                    start_date = base_date
                    end_date = base_date
            else:
                # For "last week", "last month", etc. with simple day shift
                start_date = base_date + timedelta(days=shift)
                end_date = base_date - timedelta(days=1)
        elif isinstance(shift, tuple):
            # For more complex shifts like "last month", "last quarter", etc.
            if len(shift) == 2:
                shift_value, unit = shift
                
                if unit == 'month':
                    # Calculate new year and month
                    year = base_date.year
                    month = base_date.month + shift_value
                    
                    # Adjust year if needed
                    while month <= 0:
                        year -= 1
                        month += 12
                    while month > 12:
                        year += 1
                        month -= 12
                    
                    # Get the first day of the target month
                    start_date = base_date.replace(year=year, month=month, day=1)
                    
                    # Get the last day of the target month
                    last_day = calendar.monthrange(year, month)[1]
                    end_date = start_date.replace(day=last_day)
                
                elif unit == 'quarter':
                    # Determine the current quarter
                    current_quarter = (base_date.month - 1) // 3 + 1
                    
                    # Calculate target quarter
                    target_quarter = current_quarter + shift_value
                    
                    # Adjust year if needed
                    year_shift = (target_quarter - 1) // 4
                    if target_quarter <= 0:
                        year_shift -= 1
                        target_quarter += 4 * abs(year_shift)
                    
                    target_quarter = ((target_quarter - 1) % 4) + 1
                    target_year = base_date.year + year_shift
                    
                    # Get the first month of the target quarter
                    start_month = (target_quarter - 1) * 3 + 1
                    
                    # Get the first day of the target quarter
                    start_date = base_date.replace(year=target_year, month=start_month, day=1)
                    
                    # Get the last day of the target quarter
                    if target_quarter == 4:
                        end_date = start_date.replace(month=12, day=31)
                    else:
                        end_month = target_quarter * 3
                        last_day = calendar.monthrange(target_year, end_month)[1]
                        end_date = start_date.replace(month=end_month, day=last_day)
                
                elif unit == 'year':
                    # Calculate target year
                    target_year = base_date.year + shift_value
                    
                    # Get the first day of the target year
                    start_date = base_date.replace(year=target_year, month=1, day=1)
                    
                    # Get the last day of the target year
                    end_date = start_date.replace(month=12, day=31)
            
            # Handle special cases
            elif len(shift) == 1 and shift[0] == 'year_to_date':
                # From Jan 1 to today
                start_date = base_date.replace(month=1, day=1)
                end_date = base_date
            
            elif len(shift) == 1 and shift[0] == 'month_to_date':
                # From first day of month to today
                start_date = base_date.replace(day=1)
                end_date = base_date
            
            elif len(shift) == 1 and shift[0] == 'quarter_to_date':
                # Determine the current quarter
                quarter = (base_date.month - 1) // 3 + 1
                # Get the first month of the current quarter
                start_month = (quarter - 1) * 3 + 1
                # From first day of quarter to today
                start_date = base_date.replace(month=start_month, day=1)
                end_date = base_date
        
        # Handle cases where we couldn't resolve the reference
        if 'start_date' not in locals() or 'end_date' not in locals():
            # Default to last 7 days
            start_date = base_date - timedelta(days=7)
            end_date = base_date
        
        return {
            'start_date': start_date,
            'end_date': end_date
        }
    
    def _calculate_comparison_period(self, time_period: Dict[str, datetime], comparison_type: str) -> Dict[str, datetime]:
        """
        Calculate the comparison period based on the primary time period and comparison type.
        
        Args:
            time_period: Dict with start_date and end_date
            comparison_type: Type of comparison (yoy, mom, qoq, wow)
            
        Returns:
            Dict with start_date and end_date for the comparison period
        """
        start_date = time_period['start_date']
        end_date = time_period['end_date']
        duration = (end_date - start_date).days + 1
        
        if comparison_type == 'yoy':
            # Year over year: same period last year
            return {
                'start_date': start_date.replace(year=start_date.year - 1),
                'end_date': end_date.replace(year=end_date.year - 1)
            }
        elif comparison_type == 'mom':
            # Month over month: previous month, same duration
            previous_month = start_date.month - 1
            year_shift = 0
            if previous_month == 0:
                previous_month = 12
                year_shift = -1
            
            comp_start = start_date.replace(year=start_date.year + year_shift, month=previous_month)
            comp_end = comp_start + timedelta(days=duration - 1)
            return {
                'start_date': comp_start,
                'end_date': comp_end
            }
        elif comparison_type == 'qoq':
            # Quarter over quarter: previous quarter, same duration
            current_quarter = (start_date.month - 1) // 3 + 1
            previous_quarter = current_quarter - 1
            year_shift = 0
            if previous_quarter == 0:
                previous_quarter = 4
                year_shift = -1
            
            previous_quarter_month = ((previous_quarter - 1) * 3) + 1
            comp_start = start_date.replace(year=start_date.year + year_shift, month=previous_quarter_month)
            comp_end = comp_start + timedelta(days=duration - 1)
            return {
                'start_date': comp_start,
                'end_date': comp_end
            }
        elif comparison_type == 'wow':
            # Week over week: previous week, same duration
            comp_start = start_date - timedelta(days=7)
            comp_end = end_date - timedelta(days=7)
            return {
                'start_date': comp_start,
                'end_date': comp_end
            }
        else:
            # Default to previous period of same duration
            comp_start = start_date - timedelta(days=duration)
            comp_end = start_date - timedelta(days=1)
            return {
                'start_date': comp_start,
                'end_date': comp_end
            }
    
    def format_time_period(self, time_period: Dict[str, datetime]) -> str:
        """
        Format a time period into a human-readable string.
        
        Args:
            time_period: Dict with start_date and end_date
            
        Returns:
            Human-readable description of the time period
        """
        start_date = time_period['start_date']
        end_date = time_period['end_date']
        
        # Format the dates
        start_str = start_date.strftime('%B %d, %Y')
        end_str = end_date.strftime('%B %d, %Y')
        
        # Check if it's a single day
        if start_date == end_date:
            return start_str
        
        # Check if it's a month
        if (start_date.day == 1 and 
            start_date.month == end_date.month and 
            start_date.year == end_date.year and 
            end_date.day == calendar.monthrange(end_date.year, end_date.month)[1]):
            return start_date.strftime('%B %Y')
        
        # Check if it's a year
        if (start_date.day == 1 and 
            start_date.month == 1 and 
            end_date.month == 12 and 
            end_date.day == 31 and 
            start_date.year == end_date.year):
            return start_date.strftime('%Y')
        
        # Otherwise, return range
        return f"{start_str} to {end_str}"
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the temporal analysis service.
        
        Returns:
            Dict with health status information
        """
        return {
            'service': 'temporal_analysis',
            'status': 'ok',
            'capabilities': [
                'explicit_date_extraction',
                'relative_reference_resolution',
                'date_range_extraction',
                'comparative_analysis'
            ]
        } 