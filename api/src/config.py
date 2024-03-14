import openai

from os import getenv
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Load .env file if exists
load_dotenv()

# PostgreSQL Connection
POSTGRES_USER = getenv("POSTGRES_USER")
POSTGRES_PASSWORD = getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = getenv("POSTGRES_HOST")
POSTGRES_DB = getenv("POSTGRES_DB")
POSTGRES_PORT = 5432

if POSTGRES_HOST:
    POSTGRES_ENGINE = create_engine('postgresql+psycopg2://{}:{}@{}:{}/{}'.format(POSTGRES_USER,POSTGRES_PASSWORD,POSTGRES_HOST,POSTGRES_PORT,POSTGRES_DB))
else:
    print('POSTGRES_HOST not found, please check your environment')
    exit(1)

# OpenAI Connection
OPENAI_KEY = getenv("OPENAI_KEY")

openai.api_key = OPENAI_KEY

if not OPENAI_KEY:
    print('OPENAI_KEY not found, please check your environment')
    exit(1)

# Tesseract Connection
TESSERACT_API = getenv("TESSERACT_API")

print('here in config: {}'.format(POSTGRES_ENGINE.connect()))