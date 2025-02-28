#!/usr/bin/env python3

import sys
import subprocess
import datetime
import importlib.util


def print_header(message):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(message)
    print("=" * 80)


def print_subheader(message):
    """Print a formatted subheader"""
    print("\n" + "=" * 40)
    print(message)
    print("=" * 40)


def run_command(command):
    """Run a shell command and return exit code"""
    process = subprocess.run(command, shell=True)
    return process.returncode


def run_tests():
    """Run all tests and display results"""
    # Print header with current time
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print_header(f"Running Swoop AI tests at {now}")

    # Check if pytest is installed
    pytest_installed = importlib.util.find_spec("pytest") is not None

    if not pytest_installed:
        print(
            "ERROR: pytest is not installed. Please install it with pip install pytest"
        )
        return 1

    # Check if pytest-cov is installed for coverage reporting
    pytest_cov_installed = importlib.util.find_spec("pytest_cov") is not None

    if not pytest_cov_installed:
        print(
            "WARNING: pytest-cov not installed. No coverage report will be generated."
        )
        coverage_args = ""
    else:
        coverage_args = "--cov=utils --cov-report=term"

    # Run all tests
    test_command = f"python -m pytest tests {coverage_args} -v"
    exit_code = run_command(test_command)

    if exit_code == 0:
        print_header("✅ All tests passed!")
    else:
        print_header(f"❌ Tests failed with exit code {exit_code}")

    # Run flake8 if available
    try:
        import flake8.api.legacy

        print_subheader("Running flake8 code quality checks")

        # Run flake8 on utils directory
        style_guide = flake8.api.legacy.get_style_guide(
            ignore=["E501", "E722"],  # Ignore line too long and bare except
            exclude=["__pycache__", "*.pyc", ".git", "venv"],
        )

        report = style_guide.check_files(["utils/"])

        if report.total_errors > 0:
            print(f"❌ Found {report.total_errors} code style issues")
        else:
            print("✅ No code style issues found")
    except (ImportError, ModuleNotFoundError):
        print("\n⚠️ flake8 is not installed or flake8.api.legacy is not available.")
        print("To install: pip install flake8")

    return exit_code


if __name__ == "__main__":
    sys.exit(run_tests())
