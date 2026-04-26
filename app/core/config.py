import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
API_KEY = os.getenv("API_KEY")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# PydanticAI / MindLogic Gateway 설정
BASE_URL = os.getenv("BASE_URL", "https://factchat-cloud.mindlogic.ai/v1/gateway")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3.1-flash-lite-preview")
