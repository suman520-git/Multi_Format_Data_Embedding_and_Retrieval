from langchain_openai import ChatOpenAI

from src.config import OPENAI_API_KEY, OPENAI_MODEL


def get_llm(max_tokens=300):
    """Create the OpenAI chat model used by our application."""

    if not OPENAI_API_KEY:
        raise ValueError("Add OPENAI_API_KEY to your .env file.")

    return ChatOpenAI(
        model=OPENAI_MODEL,
        api_key=OPENAI_API_KEY,
        temperature=0,
        max_tokens=max_tokens,
        timeout=60,
        max_retries=0,
    )