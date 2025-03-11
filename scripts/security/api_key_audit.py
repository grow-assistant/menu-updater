#!/usr/bin/env python3
"""
API Key and Credential Exposure Audit Tool

This script scans the codebase to identify potential exposure of API keys,
tokens, passwords, and other sensitive credentials in code, configuration files,
and version control history.

Usage:
    python api_key_audit.py [--path /path/to/scan] [--output report.json] [--check-git]
"""

import os
import re
import json
import argparse
import logging
import subprocess
from typing import Dict, List, Any, Set, Tuple
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Sensitive file patterns to flag
SENSITIVE_FILES = [
    r'\.env$',
    r'credentials\..*',
    r'\.pem$',
    r'\.key$',
    r'\.pfx$',
    r'\.p12$',
    r'\.pkcs12$',
    r'\.crt$',
    r'\.csr$',
    r'\.keystore$',
    r'secret.*\.yaml$',
    r'secret.*\.yml$',
    r'secret.*\.json$',
    r'config.*\.json$',
    r'config.*\.yaml$',
    r'config.*\.yml$',
    r'connections.*\.json$',
    r'connections.*\.yaml$',
    r'connections.*\.yml$',
]

# Patterns for potential credentials in file content
CREDENTIAL_PATTERNS = [
    # API key patterns
    (r'(?:api|app|auth|client|consumer|secret|token)[\s_-]*key[\s]*(?:=|:)[\s]*[\'"`]([^\s\'"`]{8,})[\s\'"`]', "API Key", "HIGH"),
    (r'(?:api|app|auth|client|consumer|secret)[\s_-]*token[\s]*(?:=|:)[\s]*[\'"`]([^\s\'"`]{8,})[\s\'"`]', "API Token", "HIGH"),
    
    # OAuth patterns
    (r'(?:oauth|auth).*(?:=|:)[\s]*[\'"`]([^\s\'"`]{8,})[\s\'"`]', "OAuth Token", "HIGH"),
    
    # Password patterns
    (r'(?:password|passwd|pwd)[\s]*(?:=|:)[\s]*[\'"`]([^\s\'"`]{4,})[\s\'"`]', "Password", "HIGH"),
    
    # AWS patterns
    (r'(?:aws).*_(?:key|id|token)[\s]*(?:=|:)[\s]*[\'"`]([^\s\'"`]{16,})[\s\'"`]', "AWS Key", "HIGH"),
    (r'(?:aws).*_secret[\s]*(?:=|:)[\s]*[\'"`]([^\s\'"`]{16,})[\s\'"`]', "AWS Secret", "HIGH"),
    (r'AKIA[0-9A-Z]{16}', "AWS Access Key ID", "CRITICAL"),
    
    # Google Cloud
    (r'AIza[0-9A-Za-z\\-_]{35}', "Google API Key", "CRITICAL"),
    (r'ya29\\.[0-9A-Za-z\\-_]+', "Google OAuth", "CRITICAL"),
    
    # Azure
    (r'(?:azure|ms).*(?:key|pwd|password|secret)[\s]*(?:=|:)[\s]*[\'"`]([^\s\'"`]{16,})[\s\'"`]', "Azure Key", "HIGH"),
    
    # Generic secrets and tokens
    (r'(?:secret|token)[\s]*(?:=|:)[\s]*[\'"`]([^\s\'"`]{16,})[\s\'"`]', "Secret/Token", "HIGH"),
    
    # Other service-specific patterns
    (r'STRIPE.*(?:=|:)[\s]*[\'"`](sk_live_[^\s\'"`]{24,})[\s\'"`]', "Stripe API Key", "CRITICAL"),
    (r'SG\.[^\s\'"`]{22}\.[\w-]{16}', "SendGrid API Key", "CRITICAL"),
    (r'sk-[a-zA-Z0-9]{48}', "OpenAI API Key", "CRITICAL"),
    (r'github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}', "GitHub PAT", "CRITICAL"),
    
    # Certificate private keys
    (r'-----BEGIN (?:RSA |DSA |EC )?PRIVATE KEY-----', "Private Key", "CRITICAL"),
    
    # Basic pattern for long hex/base64 strings with specific key-like labels
    (r'(?:key|token|secret|password|credential)[\s]*(?:=|:)[\s]*[\'"`]([a-zA-Z0-9+/]{32,}=*)[\s\'"`]', "Encoded Secret", "MEDIUM"),
]

# Files and directories to exclude
EXCLUDE_PATTERNS = [
    r'__pycache__',
    r'\.git',
    r'\.idea',
    r'\.vscode',
    r'\.venv',
    r'venv',
    r'env',
    r'node_modules',
    r'\.pytest_cache',
    r'\.cursor',
    r'\.log$',
    r'\.svg$',
    r'\.png$',
    r'\.jpg$',
    r'\.jpeg$',
    r'\.gif$',
    r'\.ico$',
    r'\.ttf$',
    r'\.woff$',
    r'\.woff2$',
    r'\.eot$',
    r'.*\.min\.js$',
    r'.*\.min\.css$',
    r'test_.*\.py$',
    r'.*_test\.py$',
]

# File extensions to scan
INCLUDE_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.php', '.rb', '.java', '.go', '.rs',
    '.c', '.cpp', '.cs', '.swift', '.sh', '.bash', '.yml', '.yaml', '.json',
    '.xml', '.config', '.ini', '.env', '.properties', '.toml', '.txt',
    '.md', '.cfg', '.conf'
}

@dataclass
class Finding:
    file: str
    line: int
    type: str
    risk_level: str
    matched_pattern: str
    context: str
    value_preview: str = ""  # Portion of the credential that's safe to show
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class APIKeyAuditor:
    """Audits codebase for potential API key and credential exposure."""
    
    def __init__(self, base_path: str = '.'):
        """
        Initialize the auditor.
        
        Args:
            base_path: Root directory to scan
        """
        self.base_path = Path(base_path).absolute()
        self.findings: List[Finding] = []
        self.file_count = 0
        self.sensitive_file_count = 0
        self.credential_count = 0
    
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
    
    def should_scan_file(self, file_path: Path) -> bool:
        """
        Check if a file should be scanned based on extension and exclusion patterns.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file should be scanned
        """
        # Check exclusion patterns first
        if self.should_exclude(file_path):
            return False
        
        # Check extension
        ext = file_path.suffix.lower()
        if ext in INCLUDE_EXTENSIONS:
            return True
        
        # Check if it's a sensitive file type
        filename = file_path.name
        if any(re.search(pattern, filename, re.IGNORECASE) for pattern in SENSITIVE_FILES):
            return True
            
        return False
    
    def find_files_to_scan(self) -> List[Path]:
        """
        Find all files to scan in the base path.
        
        Returns:
            List of file paths
        """
        files_to_scan = []
        
        for root, dirs, files in os.walk(self.base_path):
            # Update dirs in place to exclude directories
            dirs[:] = [d for d in dirs if not self.should_exclude(Path(root) / d)]
            
            for file in files:
                file_path = Path(root) / file
                if self.should_scan_file(file_path):
                    files_to_scan.append(file_path)
        
        return files_to_scan
    
    def is_sensitive_file(self, file_path: Path) -> bool:
        """
        Check if a file is likely to contain sensitive information based on its name.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file is considered sensitive
        """
        filename = file_path.name
        return any(re.search(pattern, filename, re.IGNORECASE) for pattern in SENSITIVE_FILES)
    
    def scan_file_for_credentials(self, file_path: Path) -> List[Finding]:
        """
        Scan a file for potential credentials.
        
        Args:
            file_path: Path to the file to scan
            
        Returns:
            List of findings
        """
        findings = []
        is_sensitive = self.is_sensitive_file(file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            lines = content.splitlines()
            
            # If file is flagged as sensitive by name, add a finding
            if is_sensitive:
                findings.append(Finding(
                    file=str(file_path.relative_to(self.base_path)),
                    line=0,
                    type="Sensitive File",
                    risk_level="MEDIUM",
                    matched_pattern="filename_pattern",
                    context=f"File with sensitive name: {file_path.name}",
                    value_preview=""
                ))
                self.sensitive_file_count += 1
            
            # Scan file content for credentials
            for line_num, line in enumerate(lines, 1):
                for pattern, cred_type, risk_level in CREDENTIAL_PATTERNS:
                    for match in re.finditer(pattern, line, re.IGNORECASE):
                        # Get context (surrounding text)
                        context_start = max(0, line_num - 2)
                        context_end = min(len(lines), line_num + 2)
                        context_lines = [f"{i+1}: {lines[i]}" for i in range(context_start, context_end)]
                        context = "\n".join(context_lines)
                        
                        # Extract credential value if captured in a group
                        value_preview = ""
                        if match.groups():
                            full_value = match.group(1)
                            # Create safe preview (first 4 chars + *** + last 2 chars)
                            if len(full_value) > 8:
                                value_preview = f"{full_value[:4]}***{full_value[-2:]}"
                            else:
                                value_preview = "***"
                        
                        findings.append(Finding(
                            file=str(file_path.relative_to(self.base_path)),
                            line=line_num,
                            type=cred_type,
                            risk_level=risk_level,
                            matched_pattern=pattern,
                            context=context,
                            value_preview=value_preview
                        ))
                        self.credential_count += 1
            
            return findings
        except Exception as e:
            logger.error(f"Error scanning {file_path}: {str(e)}")
            return []
    
    def check_git_history(self) -> List[Finding]:
        """
        Check git history for potentially exposed credentials.
        
        Returns:
            List of findings
        """
        findings = []
        
        # Check if .git directory exists
        if not (self.base_path / ".git").exists():
            logger.info("No .git directory found, skipping git history check")
            return findings
        
        try:
            # Search for potential credentials in git history
            logger.info("Checking git history for credentials (this may take some time)...")
            
            # Build patterns to search
            pattern_list = [pattern for pattern, _, _ in CREDENTIAL_PATTERNS]
            # Combine patterns, escaping special characters
            pattern_str = '|'.join(f"({p})" for p in pattern_list)
            
            # Use git grep to search history efficiently
            cmd = [
                "git", "grep", "-P", pattern_str, 
                "--all-match", "--break", "--heading",
                "--line-number", "--extended-regexp",
                "--color=always", "$(git rev-list --all)"
            ]
            
            result = subprocess.run(
                cmd, cwd=self.base_path, capture_output=True, 
                text=True, encoding='utf-8', errors='ignore'
            )
            
            if result.returncode not in (0, 1):  # 1 is "no match" which is fine
                logger.error(f"Git grep command failed: {result.stderr}")
                return findings
            
            # Parse output and create findings
            commit_pattern = re.compile(r'^([a-f0-9]{40}):(.+)$')
            current_commit = None
            current_file = None
            
            for line in result.stdout.splitlines():
                commit_match = commit_pattern.match(line)
                if commit_match:
                    current_commit = commit_match.group(1)
                    current_file = commit_match.group(2)
                elif current_commit and current_file and ":" in line:
                    line_num, content = line.split(":", 1)
                    
                    # Determine which pattern matched and the credential type
                    for pattern, cred_type, risk_level in CREDENTIAL_PATTERNS:
                        if re.search(pattern, content, re.IGNORECASE):
                            findings.append(Finding(
                                file=f"git:{current_file}",
                                line=int(line_num),
                                type=f"{cred_type} in Git History",
                                risk_level=risk_level,
                                matched_pattern=pattern,
                                context=f"Commit: {current_commit[:10]}...\nContent: {content}",
                                value_preview="***"
                            ))
                            self.credential_count += 1
            
            return findings
        except Exception as e:
            logger.error(f"Error checking git history: {str(e)}")
            return []
    
    def run(self, max_workers: int = 8, check_git: bool = False) -> Dict[str, Any]:
        """
        Run the audit on all files.
        
        Args:
            max_workers: Maximum number of worker threads
            check_git: Whether to check git history
            
        Returns:
            Audit results summary
        """
        logger.info(f"Starting API key and credential audit in {self.base_path}")
        
        files_to_scan = self.find_files_to_scan()
        self.file_count = len(files_to_scan)
        
        logger.info(f"Found {self.file_count} files to scan")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(self.scan_file_for_credentials, files_to_scan))
        
        # Flatten results
        all_findings = [item for sublist in results for item in sublist]
        
        # Check git history if requested
        if check_git:
            git_findings = self.check_git_history()
            all_findings.extend(git_findings)
        
        # Sort findings by risk level (CRITICAL first)
        risk_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        self.findings = sorted(
            all_findings, 
            key=lambda x: (risk_order.get(x.risk_level, 4), x.file, x.line)
        )
        
        logger.info(f"Analysis complete. Found {len(self.findings)} potential credential exposures")
        
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, Any]:
        """
        Generate a summary report of findings.
        
        Returns:
            Report data structure
        """
        risk_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        type_counts = {}
        file_counts = {}
        
        # Count findings by risk level and type
        for finding in self.findings:
            risk_level = finding.risk_level
            risk_counts[risk_level] += 1
            
            # Count by type
            finding_type = finding.type
            type_counts[finding_type] = type_counts.get(finding_type, 0) + 1
            
            # Count by file
            file_path = finding.file
            file_counts[file_path] = file_counts.get(file_path, 0) + 1
        
        return {
            "summary": {
                "files_analyzed": self.file_count,
                "sensitive_files": self.sensitive_file_count,
                "credential_findings": self.credential_count,
                "total_findings": len(self.findings),
                "risk_counts": risk_counts,
                "type_counts": type_counts,
                "files_with_findings": len(file_counts)
            },
            "findings": [finding.to_dict() for finding in self.findings]
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
        print("\n===== API Key and Credential Audit Summary =====")
        print(f"Files analyzed: {summary['files_analyzed']}")
        print(f"Sensitive files: {summary['sensitive_files']}")
        print(f"Credential findings: {summary['credential_findings']}")
        print(f"Total findings: {summary['total_findings']}")
        print(f"CRITICAL risk issues: {summary['risk_counts']['CRITICAL']}")
        print(f"HIGH risk issues: {summary['risk_counts']['HIGH']}")
        print(f"MEDIUM risk issues: {summary['risk_counts']['MEDIUM']}")
        print(f"LOW risk issues: {summary['risk_counts']['LOW']}")
        print("===============================================\n")
        
        # Print urgent recommendations if critical findings exist
        if summary['risk_counts']['CRITICAL'] > 0:
            print("⚠️  URGENT: Critical credential exposures found. Immediate action recommended!")
            print("   - Revoke and rotate these credentials immediately")
            print("   - Remove credentials from code and use secure storage methods")
            print("   - Clean git history if credentials are in version control")
            print("")


def main():
    """Run the auditor from command line."""
    parser = argparse.ArgumentParser(description='Audit codebase for API key and credential exposure')
    parser.add_argument('--path', default='.', help='Path to scan (default: current directory)')
    parser.add_argument('--output', default='api_key_audit_report.json', help='Output JSON file path')
    parser.add_argument('--workers', type=int, default=8, help='Number of worker threads')
    parser.add_argument('--check-git', action='store_true', help='Check git history for credentials')
    
    args = parser.parse_args()
    
    auditor = APIKeyAuditor(args.path)
    auditor.run(max_workers=args.workers, check_git=args.check_git)
    auditor.save_report(args.output)


if __name__ == "__main__":
    main() 