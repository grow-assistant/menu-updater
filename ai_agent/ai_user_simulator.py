"""
AI User Simulator for Testing

This module provides an OpenAI-powered user simulator that generates human-like queries 
and follow-up questions based on a user persona and system responses.
"""

import os
import random
import logging
import json
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger(__name__)

# Define some personas with their characteristics
DEFAULT_PERSONAS = {
    "casual_diner": {
        "description": "A casual customer who visits occasionally, has simple requests, and doesn't know the menu in detail.",
        "knowledge_level": "low",
        "patience": "moderate",
        "verbosity": "moderate",
        "formality": "casual",
        "examples": [
            "What are your most popular dishes?",
            "Do you have any vegetarian options?",
            "What's today's special?",
            "How much is the chicken sandwich?"
        ]
    },
    "frequent_customer": {
        "description": "A regular customer who knows the menu well, has specific preferences, and mentions past orders.",
        "knowledge_level": "high",
        "patience": "high",
        "verbosity": "moderate",
        "formality": "casual",
        "examples": [
            "I'd like to order my usual margherita pizza with extra basil.",
            "Last time I was here, I had that amazing tiramisu. Is it still available?",
            "Can you check my order history? I want to reorder what I got two weeks ago.",
            "Has the price of the seafood pasta changed? It used to be $18.99."
        ]
    },
    "new_user": {
        "description": "A first-time customer who needs guidance, asks basic questions, and is unfamiliar with the system.",
        "knowledge_level": "none",
        "patience": "low",
        "verbosity": "high",
        "formality": "formal",
        "examples": [
            "How does this work? Is this my first time using this system.",
            "What kind of food do you serve?",
            "Can you help me choose something? I'm not sure what to order.",
            "Do I need to create an account to place an order?"
        ]
    },
    "demanding_customer": {
        "description": "An impatient customer with specific requests, high expectations, and direct communication style.",
        "knowledge_level": "moderate",
        "patience": "very_low",
        "verbosity": "low",
        "formality": "direct",
        "examples": [
            "I need a gluten-free option and I'm in a hurry.",
            "The last time I ordered, the food was cold. Make sure it's hot this time.",
            "I want my steak medium-rare, EXACTLY medium-rare.",
            "Just tell me what your best dish is, quickly."
        ]
    },
    "indecisive_customer": {
        "description": "A customer who has trouble making decisions, asks many questions, and often changes their mind.",
        "knowledge_level": "moderate",
        "patience": "high",
        "verbosity": "very_high",
        "formality": "casual",
        "examples": [
            "I'm not sure what I want... maybe pasta? Or pizza? What do you recommend?",
            "Actually, no, I think I'll go with... hmm, what else is good?",
            "Can you tell me about the chicken dish? Actually, no, the fish one. Wait, what about the beef?",
            "I can't decide between the cheesecake and the tiramisu. Which one is more popular?"
        ]
    },
    "non_native_speaker": {
        "description": "A customer who is not fluent in English, makes grammatical errors, and may need simpler explanations.",
        "knowledge_level": "low",
        "patience": "moderate",
        "verbosity": "low",
        "formality": "formal",
        "examples": [
            "Menu have vegetable food please?",
            "How much cost for pizza?",
            "I want order food but not understand how.",
            "Last time eat here very good. What you recommend today?"
        ]
    }
}

class AIUserSimulator:
    """Simulates a user interacting with the AI system."""
    
    def __init__(self, openai_client=None, persona="casual_diner", error_rate=0.0):
        """Initialize the simulator with an OpenAI client and persona."""
        load_dotenv()
        
        self.openai_client = openai_client or OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.persona = persona
        self.persona_data = DEFAULT_PERSONAS.get(persona, DEFAULT_PERSONAS["casual_diner"])
        self.conversation_history = []
        self.error_rate = error_rate  # Probability of introducing errors
        
        logger.info(f"Initialized AI User Simulator with persona: {persona}")
        
    def set_persona(self, persona: str) -> None:
        """Set the persona for the simulator."""
        if persona in DEFAULT_PERSONAS:
            self.persona = persona
            self.persona_data = DEFAULT_PERSONAS[persona]
            logger.info(f"Changed persona to: {persona}")
        else:
            logger.warning(f"Unknown persona: {persona}. Using current persona.")
            
    def set_context(self, context: Dict[str, Any]) -> None:
        """Set additional context for the simulator."""
        self.context = context
        logger.debug(f"Set context: {context}")
            
    def generate_initial_query(self) -> str:
        """Generate an initial query based on the user persona."""
        prompt = self._build_initial_prompt()
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=prompt,
                temperature=0.7
            )
            query = response.choices[0].message.content
            
            # Potentially introduce errors if enabled
            if self.error_rate > 0 and random.random() < self.error_rate:
                query = self._introduce_error(query)
                
            logger.debug(f"Generated initial query: {query}")
            self.conversation_history.append({"role": "user", "content": query})
            return query
            
        except Exception as e:
            logger.error(f"Error generating initial query: {str(e)}")
            # Fallback to an example query from the persona
            fallback_query = random.choice(self.persona_data.get("examples", ["What's on the menu?"]))
            self.conversation_history.append({"role": "user", "content": fallback_query})
            return fallback_query
        
    def generate_followup(self, system_response: str) -> str:
        """Generate a follow-up question based on the system's response."""
        # Only add the system response to history if it's not already there
        if not self.conversation_history or self.conversation_history[-1]["role"] != "assistant" or self.conversation_history[-1]["content"] != system_response:
            self.conversation_history.append({"role": "assistant", "content": system_response})
        
        prompt = self._build_followup_prompt()
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=prompt,
                temperature=0.7
            )
            query = response.choices[0].message.content
            
            # Potentially introduce errors if enabled
            if self.error_rate > 0 and random.random() < self.error_rate:
                query = self._introduce_error(query)
                
            logger.debug(f"Generated follow-up query: {query}")
            self.conversation_history.append({"role": "user", "content": query})
            return query
            
        except Exception as e:
            logger.error(f"Error generating follow-up: {str(e)}")
            # Fallback to a generic follow-up
            fallback_query = "Can you tell me more about that?"
            self.conversation_history.append({"role": "user", "content": fallback_query})
            return fallback_query
        
    def _build_initial_prompt(self) -> List[Dict[str, str]]:
        """Build the prompt for the initial query."""
        system_prompt = f"""You are simulating a restaurant customer with the following persona:

Description: {self.persona_data['description']}
Knowledge of the restaurant: {self.persona_data['knowledge_level']}
Patience level: {self.persona_data['patience']}
Verbosity: {self.persona_data['verbosity']}
Communication style: {self.persona_data['formality']}

Generate a realistic initial query that this person would make to a restaurant's AI assistant.
The query should reflect the persona's characteristics and sound natural.
Respond with ONLY the customer's query, nothing else.
"""
        
        # Add context if available
        if hasattr(self, 'context') and self.context:
            context_str = json.dumps(self.context, indent=2)
            system_prompt += f"\n\nAdditional context about the scenario:\n{context_str}"
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Generate an initial query as this customer."}
        ]
        
    def _build_followup_prompt(self) -> List[Dict[str, str]]:
        """Build the prompt for follow-up questions."""
        system_prompt = f"""You are simulating a restaurant customer with the following persona:

Description: {self.persona_data['description']}
Knowledge of the restaurant: {self.persona_data['knowledge_level']}
Patience level: {self.persona_data['patience']}
Verbosity: {self.persona_data['verbosity']}
Communication style: {self.persona_data['formality']}

You are having a conversation with a restaurant's AI assistant.
Based on the conversation history and the last response from the assistant, 
generate a realistic follow-up query that this person would make.

Respond with ONLY the customer's follow-up query, nothing else.
"""
        
        # Create a prompt with the conversation history
        prompt = [{"role": "system", "content": system_prompt}]
        
        # Add the conversation history
        for message in self.conversation_history:
            prompt.append({
                "role": message["role"],
                "content": message["content"]
            })
            
        # Final instruction to generate follow-up
        prompt.append({
            "role": "user", 
            "content": "Based on this conversation, what would be your next question or statement as this customer?"
        })
        
        return prompt
        
    def _introduce_error(self, text: str) -> str:
        """Introduce random errors into the text to simulate user mistakes."""
        error_types = ["typo", "omission", "extra_words", "grammar"]
        error_type = random.choice(error_types)
        
        if error_type == "typo":
            # Simulate a typing error
            if len(text) > 5:
                pos = random.randint(0, len(text) - 1)
                chars = list(text)
                # Replace a character without changing the length
                chars[pos] = random.choice("abcdefghijklmnopqrstuvwxyz")
                return ''.join(chars)
                
        elif error_type == "omission":
            # Omit a word
            words = text.split()
            if len(words) > 3:
                pos = random.randint(1, len(words) - 2)  # Don't remove first or last word
                words.pop(pos)
                return ' '.join(words)
                
        elif error_type == "extra_words":
            # Add filler words
            fillers = ["like", "um", "you know", "actually", "basically"]
            words = text.split()
            if len(words) > 2:
                pos = random.randint(1, len(words) - 1)
                words.insert(pos, random.choice(fillers))
                return ' '.join(words)
                
        elif error_type == "grammar":
            # Simple grammar errors
            replacements = {
                "are": "is",
                "is": "are",
                "was": "were",
                "were": "was",
                "have": "has",
                "has": "have"
            }
            
            for original, replacement in replacements.items():
                if f" {original} " in text:
                    return text.replace(f" {original} ", f" {replacement} ", 1)
        
        # If no error was introduced, return the original text
        return text 