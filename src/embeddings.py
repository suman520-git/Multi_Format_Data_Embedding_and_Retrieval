from google.genai.types import EmbedContentConfig
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from src.config import GEMINI_EMBEDDING_MODEL, GOOGLE_API_KEY


class Gemini2Embeddings(GoogleGenerativeAIEmbeddings):
    """Adapt the LangChain integration for Gemini Embedding 2."""

    def _build_config(
        self,
        *,
        task_type=None,
        title=None,
        output_dimensionality=None,
    ):
        # Gemini Embedding 2 does not accept task_type.
        return EmbedContentConfig(
            output_dimensionality=output_dimensionality,
        )

    def embed_documents(self, texts):
        vectors = []

        for text in texts:
            # Send each document separately to obtain one vector per document.
            document_text = f"title: none | text: {text}"
            vector = super().embed_query(document_text)
            vectors.append(vector)

        return vectors

    def embed_query(self, text):
        # Identify the input as a search question.
        query_text = f"task: search result | query: {text}"
        return super().embed_query(query_text)


def get_embeddings():
    if not GOOGLE_API_KEY:
        raise ValueError("Add GOOGLE_API_KEY to your .env file.")

    return Gemini2Embeddings(
        model=GEMINI_EMBEDDING_MODEL,
        google_api_key=GOOGLE_API_KEY,
        vertexai=False,
    )