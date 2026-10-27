import math

from src.config import GEMINI_EMBEDDING_MODEL
from src.embeddings import get_embeddings


def main():
    embeddings = get_embeddings()

    documents = [
        "The application is deployed using Docker containers.",
        "The laptop has a customer rating of 4.8 out of 5.",
    ]

    question = "How is the application deployed?"

    document_vectors = embeddings.embed_documents(documents)
    query_vector = embeddings.embed_query(question)

    if len(document_vectors) != len(documents):
        raise ValueError("Expected one vector for each document.")

    dimensions = len(query_vector)

    if dimensions == 0:
        raise ValueError("The query vector is empty.")

    all_vectors = document_vectors + [query_vector]

    for vector in all_vectors:
        if len(vector) != dimensions:
            raise ValueError("Vector dimensions do not match.")

        if not all(math.isfinite(value) for value in vector):
            raise ValueError("A vector contains invalid numeric values.")

        if not any(value != 0 for value in vector):
            raise ValueError("A vector contains only zeros.")

    print("Model:", GEMINI_EMBEDDING_MODEL)
    print("Documents submitted:", len(documents))
    print("Document vectors returned:", len(document_vectors))
    print("Document dimensions:", len(document_vectors[0]))
    print("Query dimensions:", dimensions)
    print("First five query values:", query_vector[:5])
    print("Embedding checks passed.")


if __name__ == "__main__":
    main()