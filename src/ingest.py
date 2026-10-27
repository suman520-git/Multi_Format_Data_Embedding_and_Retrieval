import json
from collections import Counter

from langchain_core.documents import Document

from src.config import (
    BASE_DIR,
    GEMINI_EMBEDDING_MODEL,
    QDRANT_COLLECTION,
)
from src.vector_store import (
    EMBEDDING_DIMENSIONS,
    ensure_collection,
    get_qdrant_client,
    get_vector_store,
)


BATCH_SIZE = 5


def main():
    path = BASE_DIR / "artifacts" / "all_chunks.json"

    records = json.loads(
        path.read_text(encoding="utf-8")
    )

    documents = [
        Document(
            page_content=record["page_content"],
            metadata=dict(record["metadata"]),
        )
        for record in records
    ]

    ids = [
        document.metadata["chunk_id"]
        for document in documents
    ]

    # Check the input before making embedding requests.
    assert len(documents) == 55
    assert len(ids) == len(set(ids))
    assert all(document.page_content.strip() for document in documents)

    for document in documents:
        # Record which embedding configuration produced the vector.
        document.metadata["embedding_model"] = GEMINI_EMBEDDING_MODEL
        document.metadata["embedding_dimensions"] = EMBEDDING_DIMENSIONS

    client = get_qdrant_client()

    try:
        ensure_collection(client)

        before = client.count(
            collection_name=QDRANT_COLLECTION,
            exact=True,
        ).count

        print("Collection:", QDRANT_COLLECTION)
        print("Embedding model:", GEMINI_EMBEDDING_MODEL)
        print("Vector dimensions:", EMBEDDING_DIMENSIONS)
        print("Points before ingestion:", before)
        print("Chunks to process:", len(documents))

        # store = get_vector_store(client)

        # for start in range(0, len(documents), BATCH_SIZE):
        #     batch = documents[start:start + BATCH_SIZE]

        #     batch_ids = [
        #         document.metadata["chunk_id"]
        #         for document in batch
        #     ]

        #     print(
        #         f"Embedding and storing chunks "
        #         f"{start + 1}-{start + len(batch)}..."
        #     )

        #     # LangChain calls our embed_documents() implementation,
        #     # then sends the vectors, text, and metadata to Qdrant.
        #     store.add_documents(
        #         documents=batch,
        #         ids=batch_ids,
        #         batch_size=BATCH_SIZE,
        #         wait=True,
        #     )

        #     print("Batch stored.")

                # Read existing points before initializing the embedding model.
        existing_points = client.retrieve(
            collection_name=QDRANT_COLLECTION,
            ids=ids,
            with_payload=True,
            with_vectors=False,
        )

        existing_by_id = {
            str(point.id): point
            for point in existing_points
        }

        pending_documents = []
        skipped = 0

        for document in documents:
            chunk_id = document.metadata["chunk_id"]
            existing = existing_by_id.get(chunk_id)

            if existing is None:
                # This chunk has not been stored yet.
                pending_documents.append(document)
                continue

            payload = existing.payload or {}

            same_text = (
                payload.get("page_content")
                == document.page_content
            )

            same_metadata = (
                payload.get("metadata")
                == document.metadata
            )

            if not same_text or not same_metadata:
                # Do not silently overwrite a conflicting record.
                raise ValueError(
                    f"Stored content or metadata differs for "
                    f"chunk {chunk_id}. Inspect the difference "
                    f"before updating this record."
                )

            skipped += 1

        print("Unchanged chunks skipped:", skipped)
        print("Missing chunks to embed:", len(pending_documents))

        if pending_documents:
            # Initialize only when we actually need embeddings.
            # This also avoids the model validation request
            # when every chunk already exists unchanged.
            store = get_vector_store(client)

            for start in range(
                0, len(pending_documents), BATCH_SIZE
            ):
                batch = pending_documents[
                    start:start + BATCH_SIZE
                ]

                batch_ids = [
                    document.metadata["chunk_id"]
                    for document in batch
                ]

                print(
                    f"Embedding and storing missing chunks "
                    f"{start + 1}-{start + len(batch)}..."
                )

                store.add_documents(
                    documents=batch,
                    ids=batch_ids,
                    batch_size=BATCH_SIZE,
                    wait=True,
                )

                print("Batch stored.")

        else:
            print(
                "All input chunks already exist unchanged. "
                "No embedding requests needed."
            )

        # Retrieve our points by ID to verify actual database contents.
        stored_points = client.retrieve(
            collection_name=QDRANT_COLLECTION,
            ids=ids,
            with_payload=True,
            with_vectors=False,
        )

        assert len(stored_points) == len(documents)

        points_by_id = {
            str(point.id): point
            for point in stored_points
        }

        for document in documents:
            chunk_id = document.metadata["chunk_id"]
            point = points_by_id[chunk_id]
            payload = point.payload

            assert payload is not None
            assert payload["page_content"] == document.page_content
            assert payload["metadata"] == document.metadata

        # Read one vector back without printing thousands of numbers.
        sample = client.retrieve(
            collection_name=QDRANT_COLLECTION,
            ids=[ids[0]],
            with_payload=False,
            with_vectors=True,
        )[0]

        assert isinstance(sample.vector, list)
        assert len(sample.vector) == EMBEDDING_DIMENSIONS

        after = client.count(
            collection_name=QDRANT_COLLECTION,
            exact=True,
        ).count


        if not pending_documents:
            assert after == before, (
                "Point count changed during an unchanged run."
            )

            print("Repeat-ingestion count check passed.")

        stored_counts = Counter(
            point.payload["metadata"]["type"]
            for point in stored_points
        )

        print("\n--- Storage verification ---")
        print("Collection:", QDRANT_COLLECTION)
        print("Total collection points:", after)
        print("Verified input points:", len(stored_points))
        print("Verified points by type:", dict(stored_counts))
        print("Sample vector dimensions:", len(sample.vector))
        print("Stored text and metadata match input.")
        print("Qdrant ingestion checks passed.")

    finally:
        client.close()


if __name__ == "__main__":
    main()