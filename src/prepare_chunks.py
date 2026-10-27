import hashlib
import json
from collections import Counter, defaultdict
from uuid import NAMESPACE_URL, uuid5

from langchain_core.documents import Document

from src.config import BASE_DIR
from src.chunking import (
    chunk_word_documents,
    chunk_policy_documents,
    keep_complete_documents,
)


ARTIFACTS_DIR = BASE_DIR / "artifacts"

# These are the five descriptions you reviewed and confirmed.
REVIEWED_IMAGE_SOURCES = {
    "architecture.png",
    "deployment_flow.png",
    "sales_chart.png",
    "product_laptop.png",
    "office_workspace.png",
}


def load_documents(filename):
    """Rebuild LangChain Documents from a saved extraction."""
    path = ARTIFACTS_DIR / filename

    if not path.is_file():
        raise FileNotFoundError(
            f"Missing checkpoint file: {path}"
        )

    records = json.loads(path.read_text(encoding="utf-8"))

    return [
        Document(
            page_content=record["page_content"],
            metadata=record["metadata"],
        )
        for record in records
    ]


def main():
    pdf_chunks = load_documents("pdf_chunks.json")
    word_documents = load_documents("word_extracted.json")
    table_documents = load_documents("table_extracted.json")
    image_documents = load_documents("images_described.json")
    policy_documents = load_documents("other_extracted.json")

    # Record your confirmation on the reviewed image snapshot.
    # Do not reuse this approval for newly generated descriptions.
    image_sources = {
        document.metadata["source"]
        for document in image_documents
    }

    assert len(image_documents) == 5
    assert image_sources == REVIEWED_IMAGE_SOURCES

    for document in image_documents:
        assert (
            document.metadata["description"]
            == document.page_content
        )

        document.metadata["review_status"] = "manually_verified"
        document.metadata["review_method"] = (
            "User compared description with source image"
        )

        # Bind the review record to this exact description text.
        document.metadata["reviewed_description_sha256"] = (
            hashlib.sha256(
                document.page_content.encode("utf-8")
            ).hexdigest()
        )

    chunks = [
        *pdf_chunks,
        *chunk_word_documents(word_documents),
        *keep_complete_documents(
            table_documents,
            strategy="complete_product_row",
        ),
        *keep_complete_documents(
            image_documents,
            strategy="complete_image_description",
        ),
        *chunk_policy_documents(policy_documents),
    ]

    # A separate sequence for each source file.
    source_counts = defaultdict(int)

    for chunk in chunks:
        source_path = chunk.metadata["source_path"]
        source_index = source_counts[source_path]
        source_counts[source_path] += 1

        chunk.metadata["source_chunk_index"] = source_index

        # Same source, position, and text produce the same UUID.
        identity = json.dumps(
            [
                "multi-format-v1",
                source_path,
                source_index,
                chunk.page_content,
            ],
            ensure_ascii=False,
        )

        chunk.metadata["chunk_id"] = str(
            uuid5(NAMESPACE_URL, identity)
        )

    counts = Counter(
        chunk.metadata["type"]
        for chunk in chunks
    )

    assert set(counts) == {
        "pdf", "word", "csv", "image", "markdown", "html"
    }

    assert counts["pdf"] == 6
    assert counts["csv"] == 30
    assert counts["image"] == 5

    ids = [
        chunk.metadata["chunk_id"]
        for chunk in chunks
    ]

    assert len(ids) == len(set(ids)), "Duplicate chunk IDs."

    for chunk in chunks:
        assert chunk.page_content.strip()
        assert chunk.metadata["source"]
        assert chunk.metadata["source_path"]
        assert chunk.metadata["chunk_strategy"]

        # Reject values that cannot safely be stored as JSON.
        json.dumps(chunk.metadata, allow_nan=False)

    csv_chunks = [
        chunk
        for chunk in chunks
        if chunk.metadata["type"] == "csv"
    ]

    assert len({
        chunk.metadata["row_data"]["Product_ID"]
        for chunk in csv_chunks
    }) == 30

    # Check that Word section context survived.
    assert any(
        chunk.metadata["type"] == "word"
        and "Starting the Application" in chunk.page_content
        and "docker compose up -d" in chunk.page_content
        for chunk in chunks
    )

    # Check that the HTML shipping relationships remain together.
    assert any(
        chunk.metadata["type"] == "html"
        and "Defective product" in chunk.page_content
        and "Seller" in chunk.page_content
        and "Customer changed their mind" in chunk.page_content
        for chunk in chunks
    )

    records = [
        {
            "page_content": chunk.page_content,
            "metadata": chunk.metadata,
        }
        for chunk in chunks
    ]

    output_path = ARTIFACTS_DIR / "all_chunks.json"

    output_path.write_text(
        json.dumps(
            records,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        ),
        encoding="utf-8",
    )

    print("Total chunks:", len(chunks))
    print("Chunks by type:", dict(counts))
    print("Distinct sources:", len(source_counts))
    print("Unique chunk IDs:", len(set(ids)))
    print("Manually reviewed images:", len(image_documents))
    print(
        "Largest chunk characters:",
        max(len(chunk.page_content) for chunk in chunks),
    )

    # Print one representative chunk from every source type.
    for source_type in sorted(counts):
        example = next(
            chunk
            for chunk in chunks
            if chunk.metadata["type"] == source_type
        )

        print("\n" + "=" * 60)
        print("Type:", source_type)
        print("Metadata:")
        print(json.dumps(example.metadata, indent=2))
        print("Text:")
        print(example.page_content)

    print("\nSaved chunks:", output_path)
    print("Unified chunk preparation checks passed.")


if __name__ == "__main__":
    main()