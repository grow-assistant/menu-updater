"""
Service setup utilities for the test runner.
"""

import os
import yaml
from pathlib import Path

def setup_services(config, logger):
    """
    Set up the required services for testing.
    
    Args:
        config: Application configuration
        logger: Logger instance
        
    Returns:
        orchestrator: Configured orchestrator service
    """
    from ai_agent.utils.service_registry import ServiceRegistry
    from services.execution.sql_executor import SQLExecutor
    from services.rules.rules_service import RulesService
    from services.classification.classifier import ClassificationService
    from services.sql_generator.sql_generator_factory import SQLGeneratorFactory
    from services.response.response_generator import ResponseGenerator
    from services.orchestrator.orchestrator import OrchestratorService
    
    # Clear service registry
    ServiceRegistry.clear()
    
    # Initialize SQL executor with real database
    logger.info("Setting up SQL executor with real database")
    sql_executor = SQLExecutor(config)
    ServiceRegistry.register("sql_executor", lambda cfg: sql_executor)
    
    # Test database connection
    test_result = sql_executor.execute("SELECT 1 as test")
    if not test_result or not test_result.get("success"):
        raise Exception("Database connection test failed. Real database is required.")
    logger.info("Database connection test successful")
    
    # Create resources directory if needed for rules service
    project_root = Path(__file__).parents[2]  # Go up 2 levels from services/
    resources_dir = os.path.join(project_root, "resources")
    os.makedirs(resources_dir, exist_ok=True)
    
    # Check for rules files and create minimal versions if missing
    system_rules_path = os.path.join(resources_dir, "system_rules.yml")
    if not os.path.exists(system_rules_path):
        logger.warning(f"System rules file not found at {system_rules_path}. Creating a minimal version.")
        with open(system_rules_path, "w") as f:
            f.write("""
# System rules for AI Assistant
system:
  version: 1.0
  rules:
    - rule: "Provide accurate information based on database results"
      priority: critical
    - rule: "Never expose sensitive customer information"
      priority: critical
    - rule: "Use clear, concise language in responses"
      priority: high
            """)
    
    # Check for rules directory and create if missing
    rules_dir = os.path.join(project_root, "services", "rules")
    os.makedirs(rules_dir, exist_ok=True)
    
    # Create business rules file if missing
    business_rules_path = os.path.join(resources_dir, "business_rules.yml")
    if not os.path.exists(business_rules_path):
        logger.warning(f"Business rules file not found at {business_rules_path}. Creating a minimal version.")
        with open(business_rules_path, "w") as f:
            f.write("""
# Business rules for Restaurant Assistant
business:
  version: 1.0
  rules:
    - rule: "Always mention menu specials when asked about the menu"
      priority: medium
    - rule: "Upsell desserts when appropriate"
      priority: low
    - rule: "Provide accurate pricing information"
      priority: high
            """)
    
    # Initialize rules service
    logger.info("Setting up rules service")
    rules_service = RulesService(config)
    ServiceRegistry.register("rules", lambda cfg: rules_service)
    
    # Initialize classification service
    logger.info("Setting up classification service")
    classification_service = ClassificationService(config)
    ServiceRegistry.register("classification", lambda cfg: classification_service)
    
    # Initialize SQL generator with schema information and parameter handling
    logger.info("Setting up SQL generator with schema information")
    # Add schema info context to SQL generator config
    if "services" not in config:
        config["services"] = {}
    if "sql_generator" not in config["services"]:
        config["services"]["sql_generator"] = {}
    
    # Add database schema to SQL generator config
    if "database" in config and "schema_info" in config["database"]:
        schema_info = config["database"]["schema_info"]
        config["services"]["sql_generator"]["schema_info"] = schema_info
        logger.info(f"Added schema information for {len(schema_info.get('tables', {}))} tables")
    
    # Add additional parameter handling directives to SQL generator config
    config["services"]["sql_generator"]["parameter_handling"] = {
        "use_parameterized_queries": True,
        "location_id_param_name": "location_id",
        "default_location_id": config.get("location_id", "1"),
        "replace_placeholders": True  # Tell SQL generator to replace common placeholders
    }
    logger.info("Enhanced SQL parameter handling configured")
    
    sql_generator = SQLGeneratorFactory.create_sql_generator(config)
    ServiceRegistry.register("sql_generator", lambda cfg: sql_generator)
    
    # Initialize response generator
    logger.info("Setting up response generator")
    response_generator = ResponseGenerator(config)
    ServiceRegistry.register("response", lambda cfg: response_generator)
    
    # Create orchestrator 
    logger.info("Creating orchestrator")
    orchestrator = OrchestratorService(config)
    
    # Ensure orchestrator is using real services
    orchestrator.sql_executor = sql_executor
    orchestrator.sql_generator = sql_generator
    
    # Perform service health checks
    health_status = check_services_health(logger)
    if not all(health_status.values()):
        failed_services = [name for name, status in health_status.items() if not status]
        logger.warning(f"The following services failed health checks: {', '.join(failed_services)}")
        logger.warning("Tests will continue but may not be fully reliable")
    
    return orchestrator


def check_services_health(logger):
    """
    Perform comprehensive health checks on all services.
    
    Args:
        logger: Logger instance
        
    Returns:
        dict: Health status for each service
    """
    from ai_agent.utils.service_registry import ServiceRegistry
    
    health_status = {}
    
    # Check SQL Executor
    try:
        sql_executor = ServiceRegistry.get("sql_executor")
        test_result = sql_executor.execute("SELECT 1 as health_check")
        health_status["sql_executor"] = test_result and test_result.get("success", False)
        logger.info(f"SQL Executor health check: {'PASSED' if health_status['sql_executor'] else 'FAILED'}")
    except Exception as e:
        logger.error(f"SQL Executor health check failed: {str(e)}")
        health_status["sql_executor"] = False
    
    # Check Rules Service
    try:
        rules_service = ServiceRegistry.get("rules")
        health_status["rules_service"] = hasattr(rules_service, "get_rules")
        logger.info(f"Rules Service health check: {'PASSED' if health_status['rules_service'] else 'FAILED'}")
    except Exception as e:
        logger.error(f"Rules Service health check failed: {str(e)}")
        health_status["rules_service"] = False
    
    # Check Classification Service
    try:
        classification_service = ServiceRegistry.get("classification")
        health_status["classification_service"] = hasattr(classification_service, "classify_query")
        logger.info(f"Classification Service health check: {'PASSED' if health_status['classification_service'] else 'FAILED'}")
    except Exception as e:
        logger.error(f"Classification Service health check failed: {str(e)}")
        health_status["classification_service"] = False
    
    # Check SQL Generator
    try:
        sql_generator = ServiceRegistry.get("sql_generator")
        health_status["sql_generator"] = hasattr(sql_generator, "generate_sql")
        logger.info(f"SQL Generator health check: {'PASSED' if health_status['sql_generator'] else 'FAILED'}")
    except Exception as e:
        logger.error(f"SQL Generator health check failed: {str(e)}")
        health_status["sql_generator"] = False
    
    # Check Response Generator
    try:
        response_generator = ServiceRegistry.get("response")
        health_status["response_generator"] = hasattr(response_generator, "generate_response")
        logger.info(f"Response Generator health check: {'PASSED' if health_status['response_generator'] else 'FAILED'}")
    except Exception as e:
        logger.error(f"Response Generator health check failed: {str(e)}")
        health_status["response_generator"] = False
    
    return health_status


def setup_agents(config, logger):
    """
    Set up the Follow-Up and Critique agents for testing.
    
    Args:
        config: Application configuration
        logger: Logger instance
        
    Returns:
        tuple: (follow_up_agent, critique_agent)
    """
    from ai_agent.ai_user_simulator import AIUserSimulator
    from ai_agent.critique_agent import CritiqueAgent
    
    # Initialize the AIUserSimulator as our Follow-Up agent
    logger.info("Setting up Follow-Up agent (AIUserSimulator)")
    follow_up_agent = AIUserSimulator()
    
    # Initialize the CritiqueAgent
    logger.info("Setting up Critique agent")
    critique_agent = CritiqueAgent(config)
    
    return follow_up_agent, critique_agent 