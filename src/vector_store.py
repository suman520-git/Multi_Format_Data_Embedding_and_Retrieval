from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models

from src.config import QDRANT_URL, QDRANT_COLLECTION
from src.embeddings import get_embeddings


# This matches the successful Gemini embedding check.
EMBEDDING_DIMENSIONS = 3072


def get_qdrant_client():
    return QdrantClient(
        url=QDRANT_URL,
        timeout=60,
    )


def ensure_collection(client):
    """Create the collection if missing; validate it if present."""
    if not client.collection_exists(QDRANT_COLLECTION):
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=models.VectorParams(
                size=EMBEDDING_DIMENSIONS,
                distance=models.Distance.COSINE,
            ),
        )

        print("Created collection:", QDRANT_COLLECTION)

    collection = client.get_collection(QDRANT_COLLECTION)
    vector_config = collection.config.params.vectors

    # Our application uses one unnamed vector per point.
    if not isinstance(vector_config, models.VectorParams):
        raise ValueError(
            "Expected one unnamed vector configuration."
        )

    if vector_config.size != EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"Collection dimension is {vector_config.size}; "
            f"expected {EMBEDDING_DIMENSIONS}."
        )

    if vector_config.distance != models.Distance.COSINE:
        raise ValueError("Expected cosine distance.")

    return collection


def get_vector_store(client):
    """Connect LangChain to the existing Qdrant collection."""
    return QdrantVectorStore(
        client=client,
        collection_name=QDRANT_COLLECTION,
        embedding=get_embeddings(),
        content_payload_key="page_content",
        metadata_payload_key="metadata",
        distance=models.Distance.COSINE,
    )