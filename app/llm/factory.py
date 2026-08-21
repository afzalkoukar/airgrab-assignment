import os

from dotenv import load_dotenv

from app.llm.mock import MockQueryParser
from app.llm.base import QueryParser

load_dotenv()  # reads .env into os.environ if present; no-op otherwise

def get_parser() -> QueryParser:
    provider = os.getenv("LLM_PROVIDER", "mock")

    if provider == "mock":
        return MockQueryParser()

    # future: if provider == "openai": return OpenAIQueryParser(api_key=os.environ["LLM_API_KEY"])
    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")