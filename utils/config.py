import os 
from dotenv import load_dotenv


load_dotenv()


# Set up Postgres database credentials
db_credentials = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"), 
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_SERVER"),
    "port": os.getenv("DB_PORT")
}

# Set up OpenAI variables 
OPENAI_API_KEY  =   os.getenv("OPENAI_API_KEY")
AI_MODEL        =   'gpt-4o-mini'
# AI_MODEL        =   'gpt-4'



# Max number of tokens permitted within a conversation exchange via OpenAI API
MAX_TOKENS_ALLOWED      =   4000


# Max number of messages to exchange with OpenAI API
MAX_MESSAGES_TO_OPENAI  =   10



# An arbitrary number to provide a buffer to avoid reaching exact token limits
TOKEN_BUFFER            =   200  
