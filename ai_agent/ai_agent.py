"""
Run Modified AI Testing for the Restaurant Assistant Application

This script is a thin wrapper around the test_runner.py, providing backward compatibility 
while the new testing framework is being adopted.
"""

import os
import sys
import argparse
from pathlib import Path

# Add the project root to the Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
# Add parent directory to Python path for services module
PARENT_DIR = PROJECT_ROOT.parent
sys.path.insert(0, str(PARENT_DIR))

def parse_arguments():
    """Parse command line arguments for the AI agent."""
    parser = argparse.ArgumentParser(description="Run AI testing against the real application")
    
    # Add arguments
    parser.add_argument("--scenarios", type=str, nargs="+", help="Specific scenarios to run")
    parser.add_argument("--output", type=str, help="Output file for results")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    
    return parser.parse_args()

def main():
    """Main entry point for backward compatibility."""
    args = parse_arguments()
    print("This script is deprecated. Please use test_runner.py directly.")
    
    # Translate arguments to test_runner.py format
    test_runner_args = ["python", "-m", "ai_agent.test_runner"]
    
    # Add scenarios if specified
    if args.scenarios:
        for scenario in args.scenarios:
            test_runner_args.extend(["--scenario", scenario])
    else:
        test_runner_args.append("--all")
    
    # Add report flag
    test_runner_args.append("--report")
    
    # Add output if specified
    if args.output:
        test_runner_args.extend(["--output", args.output])
    
    # Add verbose flag if specified
    if args.verbose:
        test_runner_args.extend(["--log-level", "DEBUG"])
    
    # Print the command to run
    print(f"Running: {' '.join(test_runner_args)}")
    
    # Import and run the test_runner
    from ai_agent.test_runner import main as test_runner_main
    return test_runner_main()

if __name__ == "__main__":
    sys.exit(main()) 