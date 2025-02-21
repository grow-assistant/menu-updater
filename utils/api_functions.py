import json
import requests
from utils.config import OPENAI_API_KEY, AI_MODEL
from utils.database_functions import (
    ask_postgres_database,
    get_db_connection,
    execute_menu_update
)
from tenacity import retry, wait_random_exponential, stop_after_attempt



@retry(wait=wait_random_exponential(min=1, max=40), stop=stop_after_attempt(3))
def send_api_request_to_openai_api(messages, functions=None, function_call=None, model=AI_MODEL, openai_api_key=OPENAI_API_KEY):
    """ Send the API request to the OpenAI API via Chat Completions endpoint """
    try:
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {openai_api_key}"}
        json_data = {"model": model, "messages": messages}
        if functions: 
            json_data.update({"functions": functions})
        if function_call: 
            json_data.update({"function_call": function_call})
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=json_data)
        response.raise_for_status()

        return response
    
    except requests.RequestException as e:
        raise ConnectionError(f"Failed to connect to OpenAI API due to: {e}")


def execute_function_call(message):
    """ Run the function call provided by OpenAI's API response """
    try:
        function_name = message["function_call"]["name"]
        arguments = json.loads(message["function_call"]["arguments"])
        
        if function_name == "ask_postgres_database":
            query = arguments["query"]
            print(f"SQL query: {query} \n")
            results = ask_postgres_database(get_db_connection, query)
            print(f"Results A: {results} \n")
            
        elif function_name == "toggle_menu_item":
            query = arguments["query"]
            conn = get_db_connection()
            try:
                results = execute_menu_update(conn, query, "toggle_menu_item")
            finally:
                if conn:
                    conn.close()
            
        else:
            results = f"Error: function {function_name} does not exist"
            
        return results
        
    except Exception as e:
        return f"Error executing {message['function_call']['name']}: {str(e)}"

