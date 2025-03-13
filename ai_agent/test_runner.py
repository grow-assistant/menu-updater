"""
Main test runner module for executing tests and generating reports.
"""

import os
import sys
import argparse
import logging
import traceback
from pathlib import Path

# Import test runner modules
from ai_agent.utils.logging_setup import setup_logging
from ai_agent.utils.config_loader import load_config
from ai_agent.utils.schema_extractor import extract_schema_info

from ai_agent.services.service_setup import setup_services, setup_agents
from ai_agent.services.service_diagnostics import diagnose_sql_error, diagnose_response_issues

from ai_agent.tests.test_context import load_test_scenario, load_all_test_scenarios, build_test_context
from ai_agent.tests.test_executor import run_test, validate_sql_results
from ai_agent.tests.test_validator import validate_test_results, validate_sql_query, validate_response

from ai_agent.reporting.report_generator import generate_test_report, generate_html_report
from ai_agent.reporting.compliance_report import generate_compliance_report, generate_html_compliance_report
from ai_agent.reporting.diagnostics_report import generate_diagnostics_report, generate_html_diagnostics_report


def main():
    """
    Main entry point for the test runner.
    """
    # Parse command line arguments
    args = parse_arguments()
    
    # Setup logging
    log_dir = args.log_dir if args.log_dir else None
    logger = setup_logging(log_dir, args.log_level)
    
    try:
        logger.info("Starting test runner")
        logger.info(f"Arguments: {args}")
        
        # Load configuration
        config_path = args.config if args.config else None
        config = load_config(config_path)
        logger.info(f"Loaded configuration from {config_path if config_path else 'default path'}")
        
        # Extract schema information
        schema_path = args.schema if args.schema else None
        schema_info = extract_schema_info(schema_path)
        logger.info(f"Extracted schema information from {schema_path if schema_path else 'default path'}")
        
        # Add schema information to config
        if "database" not in config:
            config["database"] = {}
        config["database"]["schema_info"] = schema_info
        
        # Setup SQL auditing if enabled
        if args.sql_audit_log:
            logger.info(f"Setting up SQL auditing with {args.sql_retention} days retention at {args.sql_audit_log}")
            sql_audit_path = Path(args.sql_audit_log)
            sql_audit_path.mkdir(parents=True, exist_ok=True)
            config["sql_auditing"] = {
                "enabled": True,
                "path": str(sql_audit_path),
                "retention_days": args.sql_retention
            }
        else:
            config["sql_auditing"] = {"enabled": False}
            
        # Configure validation requirements
        config["validation"] = {
            "sql_validation": args.sql_validation,
            "validate_phrases": args.validate_phrases,
            "block_invalid": args.block_invalid,
            "threshold": args.threshold
        }
        
        # Configure compliance tracking
        config["compliance"] = {
            "track_compliance": args.track_compliance,
            "report_path": args.compliance_report if args.compliance_report else None
        }
        
        # Set up services
        logger.info("Setting up services")
        orchestrator = setup_services(config, logger)
        
        # Set up agents
        logger.info("Setting up agents")
        follow_up_agent, critique_agent = setup_agents(config, logger)
        
        # Initialize compliance tracking
        if args.track_compliance:
            from ai_agent.compliance.compliance_tracker import initialize_compliance_tracker, update_service_status
            logger.info("Initializing compliance tracker")
            initialize_compliance_tracker(config)
            # Update service component status
            update_service_status(orchestrator, follow_up_agent, critique_agent)
        
        # Determine which tests to run
        if args.all:
            # Run all tests
            logger.info("Running all tests")
            test_scenarios = load_all_test_scenarios(logger)
        elif args.scenario:
            # Run specific test
            logger.info(f"Running test scenario: {args.scenario}")
            scenario_data = load_test_scenario(args.scenario, logger)
            test_scenarios = {args.scenario: scenario_data}
        else:
            logger.error("No test scenario specified. Use --all or --scenario NAME")
            return 1
        
        # Run tests
        logger.info(f"Running {len(test_scenarios)} test scenarios")
        test_results = {}
        for scenario_name, scenario_data in test_scenarios.items():
            try:
                logger.info(f"Running test scenario: {scenario_name}")
                
                # Build test context with validation requirements
                test_context = build_test_context(
                    scenario_name, 
                    scenario_data, 
                    config["validation"],
                    logger
                )
                
                # Ensure SQL validation is enabled by default
                args.sql_validation = True

                # Implement logging for all SQL queries and results
                if config["sql_auditing"]["enabled"]:
                    from ai_agent.reporting.sql_audit_report import log_sql_query
                    
                    def log_sql_details(scenario_name, sql_query, sql_result, validation_status):
                        log_sql_query(
                            scenario_name=scenario_name,
                            sql_query=sql_query,
                            sql_result=sql_result,
                            validation_status=validation_status,
                            logger=logger
                        )

                # Modify the test execution to log SQL details
                result = run_test(
                    scenario_name, 
                    scenario_data, 
                    orchestrator, 
                    follow_up_agent, 
                    critique_agent, 
                    logger,
                    sql_auditing=config["sql_auditing"]
                )

                # Log SQL details after running the test
                if config["sql_auditing"]["enabled"]:
                    sql_query = sql_queries[0]["query"] if sql_queries and isinstance(sql_queries, list) and len(sql_queries) > 0 else ""
                    sql_result = sql_queries[0]["result"] if sql_queries and isinstance(sql_queries, list) and len(sql_queries) > 0 else {}
                    log_sql_details(scenario_name, sql_query, sql_result, result["sql_validation"]["is_valid"])
                
                # Perform detailed validation of the response against SQL results
                if args.sql_validation:
                    # Validate that response content matches SQL results
                    response_content = result.get("response", "")
                    sql_queries = result.get("sql_queries", [])
                    sql_results = result.get("sql_results", [])
                    
                    # Check if this is an ambiguous request
                    is_ambiguous = scenario_data.get("is_ambiguous", False) or any(tag.lower() == "ambiguous" for tag in scenario_data.get("tags", []))
                    
                    # Use the first SQL query and result if available
                    sql_query = sql_queries[0]["query"] if sql_queries and isinstance(sql_queries, list) and len(sql_queries) > 0 else ""
                    sql_result = sql_queries[0]["result"] if sql_queries and isinstance(sql_queries, list) and len(sql_queries) > 0 else {}
                    
                    is_valid_sql, sql_validation_details = validate_sql_query(
                        response_content,
                        sql_query,
                        sql_result,
                        logger,
                        is_ambiguous=is_ambiguous
                    )
                    result["sql_validation"] = {
                        "is_valid": is_valid_sql,
                        "details": sql_validation_details
                    }
                    
                    # Block invalid responses if configured
                    if args.block_invalid and not is_valid_sql:
                        logger.warning(f"Blocking invalid response for scenario {scenario_name}")
                        result["blocked"] = True
                        result["status"] = "blocked"
                
                # Validate required phrases
                if args.validate_phrases:
                    required_phrases = scenario_data.get("required_phrases", [])
                    response_content = result.get("response", "")
                    if not isinstance(response_content, str):
                        response_content = str(response_content)
                    
                    is_valid_phrases, phrase_validation_details = validate_response(
                        response_content,
                        required_phrases,
                        logger
                    )
                    result["phrase_validation"] = {
                        "is_valid": is_valid_phrases,
                        "details": phrase_validation_details
                    }
                
                test_results[scenario_name] = result
                
                # Update compliance tracker for this test scenario
                if args.track_compliance:
                    from ai_agent.compliance.compliance_tracker import update_test_scenario_status
                    update_test_scenario_status(
                        scenario_name, 
                        result["success"], 
                        result.get("sql_validation", {}).get("is_valid", False),
                        result.get("phrase_validation", {}).get("is_valid", False)
                    )
                
            except Exception as e:
                logger.error(f"Error running test scenario {scenario_name}: {str(e)}")
                logger.error(traceback.format_exc())
                test_results[scenario_name] = {
                    "scenario_name": scenario_name,
                    "status": "error",
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
        
        # Validate test results
        is_valid, validation_results = validate_test_results(test_results, args.threshold, logger)
        
        # Generate reports
        if args.report:
            logger.info("Generating reports")
            report_path = generate_test_report(test_results, args.output, logger)
            logger.info(f"Test report generated: {report_path}")
            
            html_report_path = generate_html_report(test_results, None, logger)
            logger.info(f"HTML test report generated: {html_report_path}")
            
            # Generate compliance report if enabled
            if args.track_compliance:
                from ai_agent.compliance.compliance_report import generate_compliance_tracking_report
                compliance_report_path = generate_compliance_tracking_report(
                    args.compliance_report, 
                    config,
                    logger
                )
                logger.info(f"Compliance tracking report generated: {compliance_report_path}")
            
            # Generate standard compliance report
            is_compliant, compliance_report_path = generate_compliance_report(
                test_results, None, args.threshold, logger
            )
            logger.info(f"Compliance report generated: {compliance_report_path}")
            
            is_compliant, html_compliance_report_path = generate_html_compliance_report(
                test_results, None, args.threshold, logger
            )
            logger.info(f"HTML compliance report generated: {html_compliance_report_path}")
            
            # Generate SQL audit report if SQL auditing is enabled
            if config["sql_auditing"]["enabled"]:
                from ai_agent.reporting.sql_audit_report import generate_sql_audit_report
                sql_audit_report_path = generate_sql_audit_report(
                    test_results,
                    config["sql_auditing"]["path"],
                    logger
                )
                logger.info(f"SQL audit report generated: {sql_audit_report_path}")
            
            diagnostics_report_path = generate_diagnostics_report(test_results, None, logger)
            logger.info(f"Diagnostics report generated: {diagnostics_report_path}")
            
            html_diagnostics_report_path = generate_html_diagnostics_report(test_results, None, logger)
            logger.info(f"HTML diagnostics report generated: {html_diagnostics_report_path}")
        
        # Check if validation is successful
        if is_valid:
            logger.info("All tests passed validation")
            return 0
        else:
            logger.warning("Tests failed validation")
            # Return non-zero exit code if enforce threshold is set
            if args.enforce_threshold:
                logger.warning(f"Threshold enforcement is enabled. Threshold: {args.threshold:.2%}")
                return 1
            
            # Otherwise return 0 (success) even though validation failed
            return 0
    
    except Exception as e:
        logger.error(f"Error running tests: {str(e)}")
        logger.error(traceback.format_exc())
        return 1


def parse_arguments():
    """
    Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Test runner for services and agents.")
    
    # Test selection
    selection_group = parser.add_mutually_exclusive_group(required=True)
    selection_group.add_argument("--all", action="store_true", help="Run all test scenarios")
    selection_group.add_argument("--scenario", type=str, help="Run a specific test scenario by name")
    
    # Configuration options
    parser.add_argument("--config", type=str, help="Path to configuration file")
    parser.add_argument("--schema", type=str, help="Path to schema file")
    
    # Logging options
    parser.add_argument("--log-dir", type=str, help="Directory for log files")
    parser.add_argument("--log-level", type=str, default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Logging level")
    
    # Report options
    parser.add_argument("--report", action="store_true", help="Generate test reports")
    parser.add_argument("--output", type=str, help="Output path for test report")
    
    # Validation options
    parser.add_argument("--threshold", type=float, default=0.9,
                        help="Minimum passing percentage threshold (0.0-1.0)")
    parser.add_argument("--enforce-threshold", action="store_true",
                        help="Enforce passing threshold (exit with error if not met)")
    
    # SQL validation and auditing options
    sql_group = parser.add_argument_group("SQL Validation and Auditing")
    sql_group.add_argument("--sql-validation", action="store_true", default=True,
                        help="Enable 100%% SQL validation for all responses")
    sql_group.add_argument("--sql-audit-log", type=str,
                        help="Path to store SQL audit logs (query text, results, validation status)")
    sql_group.add_argument("--sql-retention", type=int, default=90,
                        help="Number of days to retain SQL audit logs")
    
    # Compliance tracking options
    compliance_group = parser.add_argument_group("Compliance Tracking")
    compliance_group.add_argument("--track-compliance", action="store_true", default=True,
                        help="Enable compliance tracking for service components and test scenarios")
    compliance_group.add_argument("--compliance-report", type=str,
                        help="Path for the compliance tracking report")
    
    # Response validation options
    response_group = parser.add_argument_group("Response Validation")
    response_group.add_argument("--validate-phrases", action="store_true", default=True,
                        help="Validate required phrases in responses")
    response_group.add_argument("--block-invalid", action="store_true", default=True,
                        help="Block responses that fail validation")
    
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(main()) 