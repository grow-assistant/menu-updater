"""
Script to run the TestingOrchestrator for AI Agent testing
"""

import os
import json
import logging
from pathlib import Path

from ai_agent.test_orchestrator import TestingOrchestrator
from ai_agent.headless_streamlit import HeadlessStreamlit
from ai_agent.ai_user_simulator import AIUserSimulator
from ai_agent.database_validator import DatabaseValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='logs/test_run.log'
)

logger = logging.getLogger(__name__)

def main():
    """Run the testing orchestrator with basic configuration."""
    
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    logger.info("Starting AI agent test run")
    
    try:
        # Initialize components
        headless_app = HeadlessStreamlit()
        user_simulator = AIUserSimulator()
        db_validator = DatabaseValidator()
        
        # Initialize testing orchestrator
        orchestrator = TestingOrchestrator(
            headless_app=headless_app,
            user_simulator=user_simulator,
            db_validator=db_validator,
            enable_monitoring=True
        )
        
        # Run all test scenarios
        results = orchestrator.run_all_scenarios()
        
        # Generate report
        report = orchestrator.generate_report(results)
        
        # Print summary
        print(f"Total tests: {len(results)}")
        print(f"Passed: {sum(1 for r in results if r.get('status') == 'passed')}")
        print(f"Failed: {sum(1 for r in results if r.get('status') == 'failed')}")
        
        # Save report to file
        report_path = Path("test_reports/latest_report.json")
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"Test report saved to {report_path}")
        print(f"Test report saved to {report_path}")
        
    except Exception as e:
        logger.error(f"Error running tests: {str(e)}", exc_info=True)
        print(f"Error running tests: {str(e)}")

if __name__ == "__main__":
    main() 