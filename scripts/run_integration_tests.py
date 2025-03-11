#!/usr/bin/env python3
"""
Integration Test Runner

This script runs all integration tests, collects results, and generates a comprehensive report.
Use this for running comprehensive test suites before releases or major updates.

Usage:
    python run_integration_tests.py [--report-path REPORT_PATH] [--html] [--xml] [--json]
"""

import os
import sys
import argparse
import subprocess
import datetime
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test categories and their associated test files/modules
TEST_CATEGORIES = {
    "basic": [
        "tests/integration/test_updated_flow.py",
    ],
    "scenarios": [
        "tests/integration/test_scenarios.py",
    ],
    "corrections": [
        "tests/integration/test_correction_scenarios.py",
    ],
    "edge_cases": [
        "tests/integration/test_edge_cases.py::TestEdgeCases",
    ],
    "performance": [
        # These are optional and can be run separately when needed
        # "tests/integration/test_edge_cases.py::TestConcurrency",
    ],
}

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def run_test_category(category: str, test_paths: List[str], verbose: bool = False) -> Tuple[bool, Dict[str, Any]]:
    """
    Run all tests in a specific category.
    
    Args:
        category: The category name
        test_paths: List of test file paths to run
        verbose: Whether to use verbose output
        
    Returns:
        (success, results): Whether all tests passed and detailed results
    """
    logger.info(f"{Colors.HEADER}Running {category} tests...{Colors.ENDC}")
    
    # Build the pytest command
    command = ["pytest"]
    
    # Add options
    if verbose:
        command.append("-v")
    
    # Add test coverage options
    command.extend(["--cov=services", "--cov-report=term"])
    
    # Add test paths
    command.extend(test_paths)
    
    # Run the command
    start_time = datetime.datetime.now()
    process = subprocess.run(
        command, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        text=True
    )
    end_time = datetime.datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Process the results
    success = process.returncode == 0
    status = f"{Colors.GREEN}PASSED{Colors.ENDC}" if success else f"{Colors.RED}FAILED{Colors.ENDC}"
    
    # Print summary
    print(f"{Colors.BOLD}{category}{Colors.ENDC}: {status} in {duration:.2f}s")
    
    # Detailed results
    results = {
        "category": category,
        "success": success,
        "returncode": process.returncode,
        "duration": duration,
        "stdout": process.stdout,
        "stderr": process.stderr,
        "tests": test_paths
    }
    
    # Extract test counts from output if possible
    test_summary = extract_test_summary(process.stdout)
    if test_summary:
        results.update(test_summary)
        
        # Print summary
        if "passed" in test_summary:
            print(f"  Passed: {Colors.GREEN}{test_summary.get('passed', 0)}{Colors.ENDC}")
        if "failed" in test_summary:
            print(f"  Failed: {Colors.RED}{test_summary.get('failed', 0)}{Colors.ENDC}")
        if "skipped" in test_summary:
            print(f"  Skipped: {Colors.YELLOW}{test_summary.get('skipped', 0)}{Colors.ENDC}")
        if "errors" in test_summary:
            print(f"  Errors: {Colors.RED}{test_summary.get('errors', 0)}{Colors.ENDC}")
    
    return success, results


def extract_test_summary(output: str) -> Dict[str, int]:
    """Extract test counts from pytest output."""
    summary = {}
    lines = output.splitlines()
    
    # Look for the summary line
    for line in lines:
        if "passed" in line or "failed" in line or "skipped" in line or "errors" in line:
            # This might be a summary line, try to parse it
            parts = line.strip().split(',')
            
            for part in parts:
                part = part.strip()
                for category in ["passed", "failed", "skipped", "errors", "warnings"]:
                    if category in part:
                        try:
                            count = int(part.split()[0])
                            summary[category] = count
                        except (ValueError, IndexError):
                            pass
    
    return summary


def generate_html_report(results: Dict[str, Dict[str, Any]], output_path: str):
    """Generate an HTML report of test results."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SWOOP AI Integration Test Report</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1 { color: #333; }
            .summary { margin: 20px 0; }
            .category { margin: 30px 0; border: 1px solid #ddd; padding: 15px; border-radius: 5px; }
            .passed { color: green; }
            .failed { color: red; }
            .skipped { color: orange; }
            .details { margin-top: 10px; }
            .output { background-color: #f5f5f5; padding: 10px; border-radius: 5px; white-space: pre-wrap; max-height: 300px; overflow: auto; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            tr:nth-child(even) { background-color: #f9f9f9; }
        </style>
    </head>
    <body>
        <h1>SWOOP AI Integration Test Report</h1>
        <div class="summary">
            <h2>Summary</h2>
            <p>Date: {date}</p>
            <table>
                <tr>
                    <th>Category</th>
                    <th>Status</th>
                    <th>Duration (s)</th>
                    <th>Passed</th>
                    <th>Failed</th>
                    <th>Skipped</th>
                    <th>Errors</th>
                </tr>
    """.format(date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # Add summary rows
    all_passed = True
    for category, result in results.items():
        status = "Passed" if result["success"] else "Failed"
        all_passed = all_passed and result["success"]
        
        html += f"""
                <tr>
                    <td>{category}</td>
                    <td class="{'passed' if result['success'] else 'failed'}">{status}</td>
                    <td>{result['duration']:.2f}</td>
                    <td>{result.get('passed', '-')}</td>
                    <td>{result.get('failed', '-')}</td>
                    <td>{result.get('skipped', '-')}</td>
                    <td>{result.get('errors', '-')}</td>
                </tr>
        """
    
    html += """
            </table>
            <p class="{0}"><strong>Overall Result: {1}</strong></p>
        </div>
    """.format("passed" if all_passed else "failed", "PASSED" if all_passed else "FAILED")
    
    # Add detailed sections
    for category, result in results.items():
        status = "Passed" if result["success"] else "Failed"
        html += f"""
        <div class="category">
            <h2>{category}</h2>
            <p class="{'passed' if result['success'] else 'failed'}"><strong>Status: {status}</strong></p>
            <p>Duration: {result['duration']:.2f} seconds</p>
            <p>Tests:</p>
            <ul>
        """
        
        for test in result["tests"]:
            html += f"<li>{test}</li>"
        
        html += """
            </ul>
            <div class="details">
                <h3>Output</h3>
                <div class="output">{}</div>
            </div>
        </div>
        """.format(result["stdout"].replace("<", "&lt;").replace(">", "&gt;"))
    
    html += """
    </body>
    </html>
    """
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    logger.info(f"HTML report saved to {output_path}")


def generate_xml_report(results: Dict[str, Dict[str, Any]], output_path: str):
    """Generate an XML report of test results."""
    from xml.dom import minidom
    from xml.etree import ElementTree as ET
    
    root = ET.Element("testsuites")
    
    for category, result in results.items():
        testsuite = ET.SubElement(root, "testsuite")
        testsuite.set("name", category)
        testsuite.set("tests", str(result.get("passed", 0) + result.get("failed", 0) + result.get("skipped", 0)))
        testsuite.set("failures", str(result.get("failed", 0)))
        testsuite.set("errors", str(result.get("errors", 0)))
        testsuite.set("skipped", str(result.get("skipped", 0)))
        testsuite.set("time", str(result["duration"]))
        
        for test_path in result["tests"]:
            testcase = ET.SubElement(testsuite, "testcase")
            testcase.set("name", os.path.basename(test_path))
            testcase.set("classname", test_path)
            testcase.set("time", str(result["duration"] / len(result["tests"])))
            
            if not result["success"]:
                failure = ET.SubElement(testcase, "failure")
                failure.set("message", "Test failed")
                failure.text = result["stderr"]
        
        # Add stdout and stderr as properties
        properties = ET.SubElement(testsuite, "properties")
        
        stdout_prop = ET.SubElement(properties, "property")
        stdout_prop.set("name", "stdout")
        stdout_prop.set("value", result["stdout"][:1000] + "..." if len(result["stdout"]) > 1000 else result["stdout"])
        
        stderr_prop = ET.SubElement(properties, "property")
        stderr_prop.set("name", "stderr")
        stderr_prop.set("value", result["stderr"][:1000] + "..." if len(result["stderr"]) > 1000 else result["stderr"])
    
    # Format the XML nicely
    rough_string = ET.tostring(root, "utf-8")
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(pretty_xml)
    
    logger.info(f"XML report saved to {output_path}")


def generate_json_report(results: Dict[str, Dict[str, Any]], output_path: str):
    """Generate a JSON report of test results."""
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "results": results,
        "summary": {
            "categories": len(results),
            "all_passed": all(result["success"] for result in results.values()),
            "total_passed": sum(result.get("passed", 0) for result in results.values()),
            "total_failed": sum(result.get("failed", 0) for result in results.values()),
            "total_skipped": sum(result.get("skipped", 0) for result in results.values()),
            "total_errors": sum(result.get("errors", 0) for result in results.values()),
            "total_duration": sum(result["duration"] for result in results.values()),
        }
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"JSON report saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Run comprehensive integration tests")
    parser.add_argument("--report-path", default="test_reports", help="Directory to save reports")
    parser.add_argument("--html", action="store_true", help="Generate HTML report")
    parser.add_argument("--xml", action="store_true", help="Generate XML report")
    parser.add_argument("--json", action="store_true", help="Generate JSON report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--categories", nargs="+", choices=list(TEST_CATEGORIES.keys()) + ["all"], 
                        default="all", help="Test categories to run")
    
    args = parser.parse_args()
    
    # Determine which categories to run
    categories_to_run = list(TEST_CATEGORIES.keys()) if args.categories == "all" else args.categories
    
    # Make sure the report directory exists
    report_dir = Path(args.report_path)
    report_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Run tests by category
    results = {}
    overall_success = True
    
    for category in categories_to_run:
        if category in TEST_CATEGORIES:
            success, category_results = run_test_category(category, TEST_CATEGORIES[category], args.verbose)
            results[category] = category_results
            overall_success = overall_success and success
    
    # Generate reports if requested
    if args.html:
        html_path = report_dir / f"integration_test_report_{timestamp}.html"
        generate_html_report(results, str(html_path))
    
    if args.xml:
        xml_path = report_dir / f"integration_test_report_{timestamp}.xml"
        generate_xml_report(results, str(xml_path))
    
    if args.json:
        json_path = report_dir / f"integration_test_report_{timestamp}.json"
        generate_json_report(results, str(json_path))
    
    # Print overall summary
    print(f"\n{Colors.BOLD}Overall Result: {'PASSED' if overall_success else 'FAILED'}{Colors.ENDC}")
    
    # Return exit code based on test results
    return 0 if overall_success else 1


if __name__ == "__main__":
    sys.exit(main()) 