from src.config import OPENAI_MODEL
from src.generation import get_llm


def main():
    llm = get_llm()

    # A small, controlled example with a known answer.
    context = (
        "The application uses FastAPI for its HTTP API. "
        "Qdrant stores the document embeddings. "
        "Docker runs the Qdrant database."
    )

    question = "Which database stores the document embeddings?"

    messages = [
        (
            "system",
            "Answer using only the supplied context. "
            "If the answer is missing, say 'Not available in the context.' "
            "Keep the answer to one sentence.",
        ),
        (
            "human",
            f"Context:\n{context}\n\nQuestion:\n{question}",
        ),
    ]

    response = llm.invoke(messages)
    answer = response.content

    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Expected a non-empty text answer.")

    print("Model:", OPENAI_MODEL)
    print("Question:", question)
    print("Answer:", answer)
    print("Token usage:", response.usage_metadata)
    print("Generation request completed.")


if __name__ == "__main__":
    main()