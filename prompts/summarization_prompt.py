import logging
from utils.speech_utils import convert_ordinals_to_words  # Import the ordinal conversion function

# Get the logger that was configured in utils/langchain_integration.py
logger = logging.getLogger("ai_menu_updater")

def create_summarization_prompt(data_results, query, verbal_history=None):
    # Log input parameters
    logger.info(f"Summarization prompt inputs: query='{query}', verbal_history_length={len(verbal_history) if verbal_history else 0}")
    
    history_context = ""
    if verbal_history:
        # Join the verbal history with actual newline characters, not backslash n in an f-string expression
        verbal_history_text = "\n".join(verbal_history[-3:]) if verbal_history else ""
        history_context = f"""
PREVIOUS VERBAL RESPONSES:
{verbal_history_text}

AVOID REPETITION BY:
- Using different synonyms for key metrics (revenue/income/sales)
- Varying sentence structure
- Changing emphasis (sometimes highlight date first, sometimes metric)
- Using different sports analogies (when using clubhouse_legend persona)
"""

    prompt = f"""Generate a verbal response with these rules:
1. Use natural, conversational language
2. Vary sentence structure from previous responses
3. Focus on different aspects of the data each time
4. Use persona-appropriate metaphors/analogies (rotate different sports comparisons)
5. Never repeat exact phrases from previous answers
6. Alternate between these openers: 
   - Direct answer
   - Rhetorical question
   - Observational comment
   - Trend note

{history_context}

QUERY: {query}
DATA: {data_results}

Guidelines for this response:
- First sentence must use a different structure than previous responses
- Use varied synonyms for key terms (revenue/income/total sales)
- Rotate between emphasizing dates, metrics, or percentages
- Limit sports analogies to 1 per response
- Vary sentence lengths between short (3-7 words) and medium (8-15 words)
"""

    # Log the generated prompt
    logger.info(f"Generated summarization prompt: {prompt[:200]}..." if len(prompt) > 200 else prompt)
    
    return prompt

def post_process_summarization(response_text):
    """
    Apply post-processing to the summarization response text to ensure
    ordinal numbers are converted to word form for better voice synthesis.
    
    Args:
        response_text (str): Raw response from the LLM
        
    Returns:
        str: Processed response with ordinals converted to words
    """
    if not response_text:
        return response_text
        
    # Extract verbal answer section if present
    import re
    verbal_match = re.search(r"VERBAL_ANSWER:(.*?)(?=TEXT_ANSWER:|$)", response_text, re.DOTALL)
    
    if verbal_match:
        verbal_answer = verbal_match.group(1).strip()
        # Apply ordinal conversion to verbal section
        processed_verbal = convert_ordinals_to_words(verbal_answer)
        
        # Replace the original verbal section with the processed one
        processed_response = response_text.replace(
            f"VERBAL_ANSWER:{verbal_match.group(1)}", 
            f"VERBAL_ANSWER:{processed_verbal}"
        )
        
        logger.info(f"Applied ordinal conversion to VERBAL_ANSWER section")
        return processed_response
    
    # If no verbal section found, apply to whole text as fallback
    return convert_ordinals_to_words(response_text)
