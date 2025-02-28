def create_summarization_prompt(data_results, query, verbal_history=None):
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

    return f"""Generate a verbal response with these rules:
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
