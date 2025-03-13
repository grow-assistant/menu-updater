"""
Utility script to set up test scenarios for the test runner.

This script creates symbolic links or copies test scenarios from 
ai_agent/test_scenarios to the root test_scenarios directory
so that the test runner can find them correctly.
"""

import os
import sys
import shutil
import argparse
from pathlib import Path

def setup_scenarios(copy_files=False):
    """
    Set up test scenarios by creating symbolic links or copying files.
    
    Args:
        copy_files: If True, copy files instead of creating symbolic links
    """
    # Get the project root directory
    project_root = Path(os.getcwd())
    
    # Define source and destination directories
    source_dir = project_root / "ai_agent" / "test_scenarios"
    dest_dir = project_root / "test_scenarios"
    
    # Check if source directory exists
    if not source_dir.exists():
        print(f"Source directory not found: {source_dir}")
        return False
    
    # Create destination directory if it doesn't exist
    if not dest_dir.exists():
        print(f"Creating destination directory: {dest_dir}")
        dest_dir.mkdir(parents=True)
    
    # Get all JSON files in the source directory
    scenario_files = list(source_dir.glob("*.json"))
    print(f"Found {len(scenario_files)} test scenario files.")
    
    for file_path in scenario_files:
        dest_file = dest_dir / file_path.name
        
        # Remove existing symbolic link or file
        if dest_file.exists():
            if dest_file.is_symlink() or dest_file.is_file():
                print(f"Removing existing file: {dest_file}")
                dest_file.unlink()
        
        # Create symbolic link or copy file
        if copy_files:
            print(f"Copying file: {file_path} -> {dest_file}")
            shutil.copy2(file_path, dest_file)
        else:
            try:
                print(f"Creating symbolic link: {file_path} -> {dest_file}")
                dest_file.symlink_to(file_path)
            except Exception as e:
                print(f"Error creating symbolic link. Falling back to copy: {str(e)}")
                shutil.copy2(file_path, dest_file)
    
    print(f"Setup complete: {len(scenario_files)} test scenarios available in {dest_dir}")
    return True

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Set up test scenarios for the test runner."
    )
    parser.add_argument(
        "--copy", action="store_true",
        help="Copy files instead of creating symbolic links"
    )
    args = parser.parse_args()
    
    success = setup_scenarios(args.copy)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 