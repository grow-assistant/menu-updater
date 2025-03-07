"""
Classification Service for the Swoop AI application.

This package provides functionality for classifying natural language queries
into specific query types, which determines how they are processed.
"""

# Export the necessary components
__all__ = ['ClassificationService', 'QueryClassifierInterface', 'ClassificationPromptBuilder']

from services.classification.classifier import ClassificationService
from services.classification.classifier_interface import QueryClassifierInterface, classifier_interface
from services.classification.prompt_builder import ClassificationPromptBuilder, classification_prompt_builder 