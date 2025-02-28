import logging
from typing import Dict, Any
import requests


def process_query_results(
    query_result: Dict[str, Any], user_question: str, openai_client, xai_client
) -> str:
    """
    Processes SQL query results and returns a plain-language summary.
    Uses the XAI client (e.g., Google Gemini) to generate a summary of the results.
    """
    logger = logging.getLogger(__name__)

    if query_result["success"]:
        try:
            results = query_result["results"]
            count = len(results)

            # Build prompt for LLM summary (without detailed order info)
            prompt = (
                f"SQL query for '{user_question}' returned {count} orders. "
                "Provide a brief plain language summary of the results, including total orders and any notable insights. "
                "Do not include detailed order information. "
                "Important: Orders are filtered using the updated_at timestamp (not created_at)."
            )

            # (Rest of the call to xai_client using the prompt)
            headers = {
                "Authorization": f"Bearer {xai_client['XAI_TOKEN']}",
                "Content-Type": "application/json",
            }
            data = {
                "model": xai_client.get("XAI_MODEL", "grok-2-1212"),
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert at converting SQL results into concise plain language summaries.",
                    },
                    {"role": "user", "content": prompt},
                ],
            }

            response = requests.post(
                xai_client["XAI_API_URL"], headers=headers, json=data
            )
            response.raise_for_status()
            summary = response.json()["choices"][0]["message"]["content"]
            return summary

        except Exception as e:
            logger.exception(f"Error in process_query_results: {e}")
            return "Sorry, I encountered an error processing the results."
    else:
        return "The query did not execute successfully."
