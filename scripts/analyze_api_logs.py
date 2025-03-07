#!/usr/bin/env python3
"""
Utility script to analyze API call logs and identify issues or patterns.
"""
import os
import json
import argparse
import sys
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_api_logs(log_dir="logs/api_calls", days=1):
    """
    Load API call logs from the specified directory for the given number of days.
    
    Args:
        log_dir: Directory containing API call logs
        days: Number of days of logs to analyze
        
    Returns:
        List of API call log entries
    """
    logs = []
    current_date = datetime.now()
    
    # Process logs for the specified number of days
    for day_offset in range(days):
        date = current_date - timedelta(days=day_offset)
        log_date = date.strftime('%Y%m%d')
        log_file = os.path.join(log_dir, f"api_calls_{log_date}.log")
        
        if os.path.exists(log_file):
            logger.info(f"Loading API logs from {log_file}")
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                log_entry = json.loads(line)
                                logs.append(log_entry)
                            except json.JSONDecodeError:
                                logger.warning(f"Invalid JSON in log file: {line[:100]}...")
            except Exception as e:
                logger.error(f"Error reading log file {log_file}: {str(e)}")
        else:
            logger.warning(f"Log file not found: {log_file}")
    
    return logs

def analyze_api_calls(logs):
    """
    Analyze API call logs to identify patterns and issues.
    
    Args:
        logs: List of API call log entries
        
    Returns:
        Dictionary with analysis results
    """
    if not logs:
        return {"error": "No logs found to analyze"}
    
    # Initialize metrics
    metrics = {
        "total_calls": len(logs),
        "success_calls": sum(1 for log in logs if log.get("success", False)),
        "failed_calls": sum(1 for log in logs if not log.get("success", False)),
        "api_distribution": defaultdict(int),
        "endpoint_distribution": defaultdict(int),
        "error_types": Counter(),
        "average_duration": 0,
        "success_rate": 0,
        "calls_per_hour": defaultdict(int),
        "slowest_calls": [],
        "common_errors": []
    }
    
    # Calculate API and endpoint distribution
    for log in logs:
        api_name = log.get("api", "unknown")
        endpoint = log.get("endpoint", "unknown")
        key = f"{api_name}.{endpoint}"
        
        metrics["api_distribution"][api_name] += 1
        metrics["endpoint_distribution"][key] += 1
        
        # Track call times by hour
        if "timestamp" in log:
            try:
                timestamp = datetime.fromisoformat(log["timestamp"])
                hour_key = timestamp.strftime('%Y-%m-%d %H:00')
                metrics["calls_per_hour"][hour_key] += 1
            except (ValueError, TypeError):
                pass
        
        # Track errors
        if not log.get("success", False) and "error" in log:
            # Simplify error message to group similar errors
            error = log["error"]
            simplified_error = error[:100].split(":")[0].strip()
            metrics["error_types"][simplified_error] += 1
    
    # Calculate average duration
    durations = [log.get("duration_seconds", 0) for log in logs]
    metrics["average_duration"] = sum(durations) / len(durations) if durations else 0
    
    # Calculate success rate
    metrics["success_rate"] = (metrics["success_calls"] / metrics["total_calls"]) * 100 if metrics["total_calls"] > 0 else 0
    
    # Find the slowest calls
    slowest_calls = sorted(logs, key=lambda x: x.get("duration_seconds", 0), reverse=True)[:10]
    metrics["slowest_calls"] = [
        {
            "api": call.get("api"),
            "endpoint": call.get("endpoint"),
            "duration": call.get("duration_seconds"),
            "timestamp": call.get("timestamp"),
            "success": call.get("success")
        }
        for call in slowest_calls
    ]
    
    # Get most common errors
    metrics["common_errors"] = [
        {"error": error, "count": count}
        for error, count in metrics["error_types"].most_common(10)
    ]
    
    return metrics

def analyze_verbal_response_issues(logs):
    """
    Specifically analyze issues related to verbal response generation.
    
    Args:
        logs: List of API call log entries
        
    Returns:
        Dictionary with analysis results focused on verbal response issues
    """
    verbal_logs = [log for log in logs if log.get("api") == "elevenlabs"]
    
    if not verbal_logs:
        return {"error": "No verbal response logs found"}
    
    metrics = {
        "total_verbal_calls": len(verbal_logs),
        "successful_verbal_calls": sum(1 for log in verbal_logs if log.get("success", False)),
        "failed_verbal_calls": sum(1 for log in verbal_logs if not log.get("success", False)),
        "failure_reasons": Counter(),
        "average_text_length": 0,
        "average_audio_length": 0
    }
    
    # Analyze specific metrics for verbal responses
    text_lengths = []
    audio_lengths = []
    
    for log in verbal_logs:
        # Track text lengths
        if "request_summary" in log and "text_length" in log["request_summary"]:
            text_lengths.append(log["request_summary"]["text_length"])
        
        # Track audio lengths for successful calls
        if log.get("success", False) and "response_summary" in log and "audio_bytes" in log["response_summary"]:
            audio_lengths.append(log["response_summary"]["audio_bytes"])
        
        # Track failure reasons
        if not log.get("success", False) and "error" in log:
            error = log["error"]
            # Simplify error message to group similar errors
            simplified_error = error[:100].split(":")[0].strip()
            metrics["failure_reasons"][simplified_error] += 1
    
    # Calculate averages
    metrics["average_text_length"] = sum(text_lengths) / len(text_lengths) if text_lengths else 0
    metrics["average_audio_length"] = sum(audio_lengths) / len(audio_lengths) if audio_lengths else 0
    
    # Get most common failure reasons
    metrics["common_failure_reasons"] = [
        {"reason": reason, "count": count}
        for reason, count in metrics["failure_reasons"].most_common(10)
    ]
    
    return metrics

def print_report(general_metrics, verbal_metrics):
    """Print a formatted report of the analysis results."""
    print("\n" + "="*80)
    print(" "*30 + "API CALL ANALYSIS REPORT")
    print("="*80)
    
    # General metrics
    print("\nGENERAL METRICS:")
    print(f"Total API calls: {general_metrics['total_calls']}")
    print(f"Success rate: {general_metrics['success_rate']:.2f}%")
    print(f"Average duration: {general_metrics['average_duration']:.2f} seconds")
    
    # API distribution
    print("\nAPI DISTRIBUTION:")
    for api, count in general_metrics["api_distribution"].items():
        print(f"  {api}: {count} calls ({count/general_metrics['total_calls']*100:.2f}%)")
    
    # Endpoint distribution
    print("\nENDPOINT DISTRIBUTION:")
    for endpoint, count in sorted(general_metrics["endpoint_distribution"].items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {endpoint}: {count} calls")
    
    # Common errors
    print("\nMOST COMMON ERRORS:")
    for error in general_metrics["common_errors"]:
        print(f"  {error['error']}: {error['count']} occurrences")
    
    # Slowest calls
    print("\nSLOWEST CALLS:")
    for call in general_metrics["slowest_calls"][:5]:
        success_str = "SUCCESS" if call["success"] else "FAILED"
        print(f"  {call['api']}.{call['endpoint']} - {call['duration']:.2f}s - {success_str}")
    
    # Verbal response specific metrics
    print("\n" + "-"*80)
    print(" "*25 + "VERBAL RESPONSE SPECIFIC ANALYSIS")
    print("-"*80)
    
    if "error" in verbal_metrics:
        print(f"\n{verbal_metrics['error']}")
    else:
        print(f"\nTotal verbal API calls: {verbal_metrics['total_verbal_calls']}")
        print(f"Successful verbal calls: {verbal_metrics['successful_verbal_calls']} ({verbal_metrics['successful_verbal_calls']/verbal_metrics['total_verbal_calls']*100:.2f}%)")
        print(f"Failed verbal calls: {verbal_metrics['failed_verbal_calls']} ({verbal_metrics['failed_verbal_calls']/verbal_metrics['total_verbal_calls']*100:.2f}%)")
        print(f"Average text length: {verbal_metrics['average_text_length']:.2f} characters")
        print(f"Average audio length: {verbal_metrics['average_audio_length']:.2f} bytes")
        
        print("\nMOST COMMON VERBAL RESPONSE FAILURES:")
        for reason in verbal_metrics["common_failure_reasons"]:
            print(f"  {reason['reason']}: {reason['count']} occurrences")
    
    print("\n" + "="*80)

def main():
    parser = argparse.ArgumentParser(description="Analyze API call logs to identify issues")
    parser.add_argument("--days", type=int, default=1, help="Number of days of logs to analyze")
    parser.add_argument("--log-dir", type=str, default="logs/api_calls", help="Directory containing API call logs")
    args = parser.parse_args()
    
    try:
        # Load and analyze logs
        logs = load_api_logs(log_dir=args.log_dir, days=args.days)
        
        if not logs:
            print(f"No API logs found for the past {args.days} day(s)")
            return 1
        
        general_metrics = analyze_api_calls(logs)
        verbal_metrics = analyze_verbal_response_issues(logs)
        
        # Print report
        print_report(general_metrics, verbal_metrics)
        
        return 0
    
    except Exception as e:
        logger.error(f"Error analyzing logs: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 