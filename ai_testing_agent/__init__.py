"""
OpenAI Testing Agent

This package provides tools for automated testing of AI applications,
specifically focusing on simulating user interactions with Streamlit applications.
"""

__version__ = "0.1.0"

from .headless_streamlit import HeadlessStreamlit, MessageContainer
from .database_validator import DatabaseValidator
from .ai_user_simulator import AIUserSimulator
from .critique_agent import CritiqueAgent
from .test_orchestrator import TestingOrchestrator
from .scenario_library import ScenarioLibrary
from .conversation_analyzer import ConversationAnalyzer
from .monitoring import TestMonitor, ConsoleMonitorCallback, create_test_monitor

__all__ = [
    'HeadlessStreamlit',
    'MessageContainer',
    'DatabaseValidator',
    'AIUserSimulator',
    'CritiqueAgent',
    'TestingOrchestrator',
    'ScenarioLibrary',
    'ConversationAnalyzer',
    'TestMonitor',
    'ConsoleMonitorCallback',
    'create_test_monitor',
] 