"""
Critique Agent for AI Testing

This module provides the CritiqueAgent class, which analyzes system responses
and terminal logs to generate developer-focused critiques and recommendations.
"""

import os
import re
import logging
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI

from .database_validator import DatabaseValidator

logger = logging.getLogger(__name__)

class CritiqueAgent:
    """Generates developer-focused critiques of system responses and implementation."""
    
    def __init__(self, openai_client=None, db_validator: Optional[DatabaseValidator]=None):
        """Initialize the critique agent.
        
        Args:
            openai_client: The OpenAI client to use for generating critiques.
                If None, a new client will be created using the OPENAI_API_KEY env var.
            db_validator: A DatabaseValidator instance to validate responses against the database.
        """
        load_dotenv()
        self.openai_client = openai_client or OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.db_validator = db_validator
        logger.info("Initialized CritiqueAgent")
        
    def generate_critiques(self, query: str, response: str, 
                          conversation_history: List[Dict[str, str]], 
                          terminal_logs: Optional[str]=None) -> Dict[str, List[Dict[str, Any]]]:
        """Generate critiques for a specific interaction.
        
        Args:
            query: The user query that prompted the response
            response: The system's response to critique
            conversation_history: List of conversation turns
            terminal_logs: Terminal logs from processing the query (optional)
            
        Returns:
            Dict containing "critiques" and "recommendations" lists
        """
        # Build a prompt that asks for developer-focused critiques
        prompt = self._build_critique_prompt(query, response, conversation_history, terminal_logs)
        
        logger.debug(f"Generating critiques for response: {response[:50]}...")
        
        # Get critiques from OpenAI
        try:
            ai_response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=prompt,
                temperature=0.7
            )
            
            # Parse critiques and recommendations from the response
            response_text = ai_response.choices[0].message.content
            critiques = self._parse_critiques(response_text)
            recommendations = self._parse_recommendations(response_text)
            
            # Add database validation results if available
            if self.db_validator:
                validation_result = self.db_validator.validate_response(response, "general")
                if validation_result.get("valid") is False and validation_result.get("validation_results"):
                    explanation = validation_result["validation_results"][0].get("explanation", "Unknown error")
                    critiques.append({
                        "type": "factual_error",
                        "severity": "high",
                        "message": f"CRITIQUE: Response contains factual inaccuracies. {explanation}",
                        "suggestion": "Verify data against the database before responding."
                    })
                    
            logger.info(f"Generated {len(critiques)} critiques and {len(recommendations)} recommendations")
            return {
                "critiques": critiques,
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"Error generating critiques: {str(e)}", exc_info=True)
            return {
                "critiques": [],
                "recommendations": []
            }
        
    def _build_critique_prompt(self, query: str, response: str, 
                              conversation_history: List[Dict[str, str]], 
                              terminal_logs: Optional[str]=None) -> List[Dict[str, str]]:
        """Build a prompt for generating critiques.
        
        Args:
            query: The user query that prompted the response
            response: The system's response to critique
            conversation_history: List of conversation turns
            terminal_logs: Terminal logs from processing the query (optional)
            
        Returns:
            List of message dictionaries forming the prompt
        """
        system_content = """You are an expert critique agent and developer advisor for conversational AI systems.
Your job is to identify issues with the system's responses and provide actionable feedback to developers.

For user experience issues, format your critiques as "CRITIQUE: [critique message]" followed by suggestions for improvement.
Focus on clarity, factual correctness, helpfulness, UI/UX issues, and conversation flow.

As an expert developer, also analyze terminal logs (if provided) and implementation details to provide development recommendations.
Format these as "RECOMMENDATION: [recommendation]" with specific, actionable guidance on:
- Code architecture improvements
- Performance optimizations
- Bug fixes with implementation details
- API design enhancements
- Developer workflow improvements
- Refactoring opportunities

Be specific and technical in your recommendations, as these will be used directly by developers."""

        user_content = f"""Analyze the following conversation and provide critiques:

Conversation History:
{self._format_conversation_history(conversation_history)}

Latest User Query: {query}

System Response: {response}
"""

        if terminal_logs:
            user_content += f"""
Terminal Logs:
```
{terminal_logs}
```
"""

        user_content += """
Provide both user-facing critiques (CRITIQUE:) and developer-focused recommendations (RECOMMENDATION:) based on the above information.
"""

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]
        
    def _parse_critiques(self, critique_text: str) -> List[Dict[str, Any]]:
        """Parse critiques from the OpenAI response.
        
        Args:
            critique_text: The text containing critiques to parse
            
        Returns:
            List of parsed critiques as dictionaries
        """
        critiques = []
        
        # Extract critiques using regex
        critique_pattern = r"CRITIQUE:\s*(.*?)(?=CRITIQUE:|RECOMMENDATION:|$)"
        matches = re.finditer(critique_pattern, critique_text, re.DOTALL)
        
        for i, match in enumerate(matches):
            critique_content = match.group(1).strip()
            
            # Determine severity (this could be more sophisticated)
            severity = "medium"  # Default
            if "critical" in critique_content.lower():
                severity = "critical"
            elif "serious" in critique_content.lower() or "significant" in critique_content.lower():
                severity = "high"
            elif "minor" in critique_content.lower() or "small" in critique_content.lower():
                severity = "low"
                
            # Extract suggestion if present
            suggestion = ""
            if "suggestion:" in critique_content.lower():
                parts = critique_content.split("Suggestion:", 1)
                if len(parts) == 2:
                    critique_content = parts[0].strip()
                    suggestion = parts[1].strip()
                
            critiques.append({
                "id": f"critique_{i+1}",
                "type": self._determine_critique_type(critique_content),
                "severity": severity,
                "message": f"CRITIQUE: {critique_content}",
                "suggestion": suggestion
            })
            
        return critiques
        
    def _parse_recommendations(self, text: str) -> List[Dict[str, Any]]:
        """Parse developer recommendations from the OpenAI response.
        
        Args:
            text: The text containing recommendations to parse
            
        Returns:
            List of parsed recommendations as dictionaries
        """
        recommendations = []
        
        # Extract recommendations using regex
        recommendation_pattern = r"RECOMMENDATION:\s*(.*?)(?=CRITIQUE:|RECOMMENDATION:|$)"
        matches = re.finditer(recommendation_pattern, text, re.DOTALL)
        
        for i, match in enumerate(matches):
            recommendation_content = match.group(1).strip()
            
            # Determine category based on content
            category = self._determine_recommendation_category(recommendation_content)
            
            # Determine priority
            priority = "medium"  # Default
            if "high priority" in recommendation_content.lower() or "critical" in recommendation_content.lower():
                priority = "high"
            elif "low priority" in recommendation_content.lower() or "minor" in recommendation_content.lower():
                priority = "low"
            
            recommendations.append({
                "id": f"recommendation_{i+1}",
                "category": category,
                "priority": priority,
                "message": f"RECOMMENDATION: {recommendation_content}"
            })
            
        return recommendations
        
    def _determine_recommendation_category(self, content: str) -> str:
        """Categorize the recommendation based on its content.
        
        Args:
            content: The recommendation text to categorize
            
        Returns:
            Category string
        """
        content_lower = content.lower()
        
        if any(term in content_lower for term in ["architecture", "structure", "design pattern", "component"]):
            return "architecture"
        elif any(term in content_lower for term in ["performance", "optimization", "speed", "memory", "resource"]):
            return "performance"
        elif any(term in content_lower for term in ["bug", "fix", "issue", "error", "exception"]):
            return "bug_fix"
        elif any(term in content_lower for term in ["api", "interface", "endpoint", "contract"]):
            return "api_design"
        elif any(term in content_lower for term in ["workflow", "process", "development", "testing"]):
            return "workflow"
        elif any(term in content_lower for term in ["refactor", "clean", "improve", "simplify"]) and not "make improvements" in content_lower:
            return "refactoring"
        else:
            return "general"
        
    def _determine_critique_type(self, critique_content: str) -> str:
        """Determine the type of critique based on content.
        
        Args:
            critique_content: The critique text to categorize
            
        Returns:
            Critique type string
        """
        content_lower = critique_content.lower()
        
        if any(term in content_lower for term in ["incorrect", "wrong", "inaccurate", "fact", "untrue"]):
            return "factual_error"
        elif any(term in content_lower for term in ["unclear", "confusing", "ambiguous"]):
            return "clarity_issue"
        elif any(term in content_lower for term in ["ui", "interface", "display", "button", "input"]):
            return "ui_issue"
        elif any(term in content_lower for term in ["slow", "performance", "lag", "time"]):
            return "performance_issue"
        elif any(term in content_lower for term in ["context", "history", "previous", "earlier"]):
            return "context_issue"
        elif any(term in content_lower for term in ["grammar", "spelling", "typo", "language"]):
            return "language_issue"
        else:
            return "general_issue"
            
    def _format_conversation_history(self, conversation_history: List[Dict[str, str]]) -> str:
        """Format the conversation history for the prompt.
        
        Args:
            conversation_history: List of conversation message dictionaries
            
        Returns:
            Formatted conversation history string
        """
        formatted = []
        for message in conversation_history:
            role = message["role"].upper()
            content = message["content"]
            formatted.append(f"{role}: {content}")
        return "\n".join(formatted) 