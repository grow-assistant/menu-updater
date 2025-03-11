#!/usr/bin/env python3
"""
SQL Injection Vulnerability Audit Tool

This script scans the codebase to identify potential SQL injection vulnerabilities
by analyzing direct SQL queries and checking for proper parameter binding.

Usage:
    python sql_injection_audit.py [--path /path/to/scan] [--output report.json]
"""

import os
import re
import json
import argparse
import logging
from typing import Dict, List, Any, Tuple, Set
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Patterns to identify SQL queries
SQL_PATTERNS = [
    r'(?:execute|executemany|query|raw|execute_query)\s*\(\s*([\'\"])(.*?(?<!\\))\1',
    r'(?:text|sql|query)\s*=\s*([\'\"])((?:[^\1\\]|\\.)*SELECT[^;]*)\1',
    r'(?:text|sql|query)\s*=\s*([\'\"])((?:[^\1\\]|\\.)*INSERT[^;]*)\1',
    r'(?:text|sql|query)\s*=\s*([\'\"])((?:[^\1\\]|\\.)*UPDATE[^;]*)\1',
    r'(?:text|sql|query)\s*=\s*([\'\"])((?:[^\1\\]|\\.)*DELETE[^;]*)\1',
    r'(?:pd\.read_sql|sqlalchemy\.text)\(\s*([\'\"])(.*?(?<!\\))\1',
]

# Patterns that suggest safe query construction (parameterized queries)
SAFE_PATTERNS = [
    r'%s',                 # Python DB API placeholders
    r'%\(\w+\)s',          # Named parameters
    r'\?',                 # SQLite/ODBC style
    r':\w+',               # Oracle style
    r'\$\d+',              # PostgreSQL style
    r'@\w+',               # SQL Server style
    r'param\w*=',          # Parameter passing
    r'params\s*=',         # Parameters dictionary
    r'parameterized=True',  # Explicit parameterization
    r'convert_unicode=True',  # Usually with safe construction
]

# Patterns that suggest unsafe query construction (string concatenation/formatting)
UNSAFE_PATTERNS = [
    r'\+\s*[\'"]',        # String concatenation
    r'%\s*\(',            # Old-style string formatting
    r'\.format\(',        # New-style string formatting
    r'f[\'"].*{.*}',      # f-strings with variables
    r'\s*\+\s*\w+',       # Variable concatenation
    r'str\s*\(',          # Type casting that might be for concatenation
]

# Files and directories to exclude
EXCLUDE_PATTERNS = [
    r'__pycache__',
    r'\.git',
    r'\.venv',
    r'env',
    r'venv',
    r'\.pytest_cache',
    r'\.cursor',
    r'test_*\.py',
    r'*_test\.py',
    r'tests/'
]

class SQLInjectionAuditor:
    """Audits codebase for potential SQL injection vulnerabilities."""
    
    def __init__(self, base_path: str = '.'):
        """
        Initialize the auditor.
        
        Args:
            base_path: Root directory to scan
        """
        self.base_path = Path(base_path).absolute()
        self.findings = []
        self.file_count = 0
        self.sql_query_count = 0
        self.vulnerability_count = 0
    
    def should_exclude(self, path: Path) -> bool:
        """
        Check if a path should be excluded from analysis.
        
        Args:
            path: Path to check
            
        Returns:
            True if path should be excluded
        """
        path_str = str(path)
        return any(re.search(pattern, path_str) for pattern in EXCLUDE_PATTERNS)
    
    def find_python_files(self) -> List[Path]:
        """
        Find all Python files in the base path.
        
        Returns:
            List of Python file paths
        """
        python_files = []
        
        for root, dirs, files in os.walk(self.base_path):
            # Update dirs in place to exclude directories
            dirs[:] = [d for d in dirs if not self.should_exclude(Path(root) / d)]
            
            for file in files:
                if file.endswith('.py') and not self.should_exclude(Path(root) / file):
                    python_files.append(Path(root) / file)
        
        return python_files
    
    def extract_sql_queries(self, content: str, file_path: Path) -> List[Dict[str, Any]]:
        """
        Extract SQL queries from file content.
        
        Args:
            content: File content to analyze
            file_path: Path to the file being analyzed
            
        Returns:
            List of queries with metadata
        """
        queries = []
        
        for pattern in SQL_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE | re.DOTALL):
                query_text = match.group(2)
                line_number = content[:match.start()].count('\n') + 1
                context_start = max(0, match.start() - 50)
                context_end = min(len(content), match.end() + 50)
                context = content[context_start:context_end].strip()
                
                # Check for safe/unsafe patterns
                safe_indicators = [p for p in SAFE_PATTERNS if re.search(p, context)]
                unsafe_indicators = [p for p in UNSAFE_PATTERNS if re.search(p, context)]
                
                risk_level = self._assess_risk(safe_indicators, unsafe_indicators)
                
                queries.append({
                    "file": str(file_path.relative_to(self.base_path)),
                    "line": line_number,
                    "query": query_text.strip(),
                    "context": context,
                    "safe_indicators": safe_indicators,
                    "unsafe_indicators": unsafe_indicators,
                    "risk_level": risk_level
                })
        
        return queries
    
    def _assess_risk(self, safe_indicators: List[str], unsafe_indicators: List[str]) -> str:
        """
        Assess the risk level of a query based on indicators.
        
        Args:
            safe_indicators: List of safe patterns found
            unsafe_indicators: List of unsafe patterns found
            
        Returns:
            Risk level: "LOW", "MEDIUM", or "HIGH"
        """
        if unsafe_indicators and not safe_indicators:
            return "HIGH"
        elif unsafe_indicators and safe_indicators:
            return "MEDIUM"
        elif not unsafe_indicators and safe_indicators:
            return "LOW"
        else:
            # No clear indicators either way
            return "MEDIUM"  # Conservative approach
    
    def analyze_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Analyze a single file for SQL injection vulnerabilities.
        
        Args:
            file_path: Path to file to analyze
            
        Returns:
            List of findings for this file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            queries = self.extract_sql_queries(content, file_path)
            
            return queries
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {str(e)}")
            return []
    
    def run(self, max_workers: int = 8) -> Dict[str, Any]:
        """
        Run the audit on all Python files.
        
        Args:
            max_workers: Maximum number of worker threads
            
        Returns:
            Audit results summary
        """
        logger.info(f"Starting SQL injection audit in {self.base_path}")
        
        python_files = self.find_python_files()
        self.file_count = len(python_files)
        
        logger.info(f"Found {self.file_count} Python files to analyze")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(self.analyze_file, python_files))
        
        # Flatten results
        all_findings = [item for sublist in results for item in sublist]
        
        # Count and categorize
        self.sql_query_count = len(all_findings)
        self.vulnerability_count = sum(1 for f in all_findings if f["risk_level"] in ["MEDIUM", "HIGH"])
        
        # Sort findings by risk level (HIGH first)
        risk_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        self.findings = sorted(all_findings, key=lambda x: risk_order.get(x["risk_level"], 3))
        
        logger.info(f"Analysis complete. Found {self.sql_query_count} SQL queries with {self.vulnerability_count} potential vulnerabilities")
        
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, Any]:
        """
        Generate a summary report of findings.
        
        Returns:
            Report data structure
        """
        risk_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        file_risks = {}
        
        # Count findings by risk level
        for finding in self.findings:
            risk_level = finding["risk_level"]
            risk_counts[risk_level] += 1
            
            # Track highest risk per file
            file_path = finding["file"]
            if file_path not in file_risks or risk_order[risk_level] < risk_order[file_risks[file_path]]:
                file_risks[file_path] = risk_level
        
        return {
            "summary": {
                "files_analyzed": self.file_count,
                "sql_queries_found": self.sql_query_count,
                "vulnerability_count": self.vulnerability_count,
                "risk_counts": risk_counts
            },
            "findings": self.findings
        }
    
    def save_report(self, output_path: str) -> None:
        """
        Save the report to a JSON file.
        
        Args:
            output_path: Path to save the report
        """
        report = self.generate_report()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"Report saved to {output_path}")
        
        # Print summary to console
        summary = report["summary"]
        print("\n===== SQL Injection Audit Summary =====")
        print(f"Files analyzed: {summary['files_analyzed']}")
        print(f"SQL queries found: {summary['sql_queries_found']}")
        print(f"Potential vulnerabilities: {summary['vulnerability_count']}")
        print(f"HIGH risk issues: {summary['risk_counts']['HIGH']}")
        print(f"MEDIUM risk issues: {summary['risk_counts']['MEDIUM']}")
        print(f"LOW risk issues: {summary['risk_counts']['LOW']}")
        print("=======================================\n")


def main():
    """Run the auditor from command line."""
    parser = argparse.ArgumentParser(description='Audit codebase for SQL injection vulnerabilities')
    parser.add_argument('--path', default='.', help='Path to scan (default: current directory)')
    parser.add_argument('--output', default='sql_injection_report.json', help='Output JSON file path')
    parser.add_argument('--workers', type=int, default=8, help='Number of worker threads')
    
    args = parser.parse_args()
    
    auditor = SQLInjectionAuditor(args.path)
    auditor.run(max_workers=args.workers)
    auditor.save_report(args.output)


if __name__ == "__main__":
    main() 