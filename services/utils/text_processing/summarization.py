"""
Text summarization and cleaning utilities.

This module provides functions for summarizing text and cleaning it
for text-to-speech processing.
"""

import re
from typing import Optional, Dict, Any, List

from services.utils.logging import get_logger

logger = get_logger(__name__)


def summarize_text(
    text: str,
    max_length: int = 200,
    ai_client = None,
    config: Optional[Dict[str, Any]] = None
) -> str:
    """
    Summarize text to a specified maximum length.
    
    Uses AI if available, otherwise falls back to simple truncation.
    
    Args:
        text: Text to summarize
        max_length: Maximum length of the summary in characters
        ai_client: Optional AI client for generating summaries
        config: Optional configuration parameters
        
    Returns:
        str: Summarized text
    """
    if not text:
        return ""
        
    # If text is already shorter than max_length, return it as is
    if len(text) <= max_length:
        return text
        
    config = config or {}
        
    if not ai_client:
        # Simple truncation if no AI client
        # Try to break at sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        summary = ""
        for sentence in sentences:
            if len(summary) + len(sentence) + 1 <= max_length:
                summary += " " + sentence if summary else sentence
            else:
                break
                
        if not summary:  # If we couldn't fit even one sentence
            return text[:max_length] + "..."
            
        return summary
        
    try:
        system_prompt = f"""Summarize the following text to be under {max_length} characters.
Preserve the most important information while making it sound natural.
The summary should be suitable for text-to-speech conversion."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
        
        response = ai_client.chat.completions.create(
            model=config.get("summary_model", "gpt-3.5-turbo"),
            messages=messages,
            temperature=0.3,  # Lower temperature for more consistent summaries
            max_tokens=config.get("summary_max_tokens", 100)
        )
        
        summary = response.choices[0].message.content
        logger.info(f"Generated summary: {len(summary)} chars")
        return summary
        
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        # Fallback to simple truncation
        return text[:max_length] + "..."


def clean_for_tts(text: str) -> str:
    """
    Clean text to make it more suitable for text-to-speech processing.
    
    Args:
        text: Text to clean
        
    Returns:
        str: Cleaned text suitable for TTS
    """
    # Remove markdown formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*(.*?)\*', r'\1', text)  # Italic
    text = re.sub(r'__(.*?)__', r'\1', text)  # Underline
    
    # Remove markdown tables and replace with simple statements
    if "| " in text and " |" in text:
        text = "I have the information you requested. Please check the text response for details."
        
    # Remove URLs
    text = re.sub(r'https?://\S+', 'link', text)
    
    # Remove markdown code blocks
    text = re.sub(r'```.*?```', 'code example', text, flags=re.DOTALL)
    
    # Handle bullet points
    text = re.sub(r'^[-*]\s+', 'Bullet point: ', text, flags=re.MULTILINE)
    
    # Replace newlines with spaces for better flow
    text = re.sub(r'\n+', ' ', text)
    
    # Fix spacing issues
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Handle numbers and currency for better TTS pronunciation
    text = re.sub(r'\$(\d+)\.(\d+)', r'$\1 dollars and \2 cents', text)
    text = re.sub(r'\$(\d+)', r'$\1 dollars', text)
    
    # Handle dates for better pronunciation
    text = re.sub(r'(\d{1,2})/(\d{1,2})/(\d{4})', r'\1 \2 \3', text)
    
    # Handle time formats
    text = re.sub(r'(\d{1,2}):(\d{2})([ap]m)', r'\1 \2 \3', text, flags=re.IGNORECASE)
    
    return text 


def extract_key_sentences(text: str, max_sentences: int = 2) -> str:
    """
    Extracts key sentences from text for TTS purposes.
    
    Args:
        text: The text to extract sentences from
        max_sentences: Maximum number of sentences to extract
        
    Returns:
        str: Extracted sentences joined together
    """
    if not text:
        return ""
        
    # Split text into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    
    # If we have fewer sentences than max_sentences, return all
    if len(sentences) <= max_sentences:
        return clean_for_tts(text)
    
    # For longer text, extract first sentence and last sentence if max_sentences=2
    # or just first sentence if max_sentences=1
    extracted = []
    
    # Always include the first sentence as it usually contains the main point
    extracted.append(sentences[0])
    
    # If we want more than one sentence, add the last one 
    # (often contains conclusion or next steps)
    if max_sentences > 1 and len(sentences) > 1:
        extracted.append(sentences[-1])
    
    # Join the extracted sentences
    result = " ".join(extracted)
    
    # Apply TTS cleaning
    return clean_for_tts(result) 