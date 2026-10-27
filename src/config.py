import os
from pathlib import Path

from dotenv import load_dotenv


# Find the project root using this file's location.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load local settings while preserving existing environment variables.
load_dotenv(BASE_DIR / ".env", override=False)


def required_setting(name):
    """Read a setting and report a clear error if it is missing."""
    value = os.getenv(name, "").strip()

    if not value:
        raise ValueError(f"Missing required setting: {name}")

    return value


APP_NAME = required_setting("APP_NAME")
APP_ENV = required_setting("APP_ENV")

QDRANT_URL = required_setting("QDRANT_URL")
QDRANT_COLLECTION = required_setting("QDRANT_COLLECTION")

GEMINI_EMBEDDING_MODEL = required_setting("GEMINI_EMBEDDING_MODEL")

# Credentials become mandatory when we initialize their API clients.
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

OPENAI_MODEL = required_setting("OPENAI_MODEL")