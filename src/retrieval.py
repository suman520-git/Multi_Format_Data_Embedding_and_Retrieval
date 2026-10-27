from src.config import QDRANT_COLLECTION
from src.vector_store import (
    get_qdrant_client,
    get_vector_store,
)
from qdrant_client import models

import re


def build_filter(source_type=None, source_path=None, page=None):
    """Combine supplied metadata conditions using AND."""
    conditions = []

    if source_type is not None:
        allowed_types = {
            "pdf", "word", "csv", "excel",
            "image", "markdown", "html",
        }

        if source_type not in allowed_types:
            raise ValueError("Unsupported source type.")

        conditions.append(
            models.FieldCondition(
                key="metadata.type",
                match=models.MatchValue(value=source_type),
            )
        )

    if source_path is not None:
        if not isinstance(source_path, str) or not source_path.strip():
            raise ValueError("source_path must be a nonempty string.")

        conditions.append(
            models.FieldCondition(
                key="metadata.source_path",
                match=models.MatchValue(value=source_path),
            )
        )

    if page is not None:
        if type(page) is not int or page < 1:
            raise ValueError("page must be a positive integer.")

        conditions.append(
            models.FieldCondition(
                key="metadata.page",
                match=models.MatchValue(value=page),
            )
        )

    return models.Filter(must=conditions) if conditions else None


def find_named_source(query):
    """Recognize a single simple filename explicitly named in a question."""
    pattern = (
        r"(?<![\w.-])"
        r"[\w-]+\."
        r"(?:pdf|docx|csv|xlsx|png|jpg|jpeg|md|html|htm)"
        r"\b"
    )

    filenames = list(dict.fromkeys(
        re.findall(pattern, query, flags=re.IGNORECASE)
    ))

    if len(filenames) > 1:
        raise ValueError(
            "Automatic filename filtering currently supports one file. "
            "Ask about one file at a time."
        )

    return filenames[0] if filenames else None




def search(query,
    k=5,
    *,
    source_type=None,
    source_path=None,
    page=None,):
    """Search all stored formats and return the closest chunks."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query must be a nonempty string.")

    if type(k) is not int or not 1 <= k <= 20:
        raise ValueError("k must be an integer between 1 and 20.")

    query = query.strip()

    query_filter = build_filter(
        source_type=source_type,
        source_path=source_path,
        page=page,
    )

    named_source = find_named_source(query)

    if named_source is not None:
        filename_condition = models.FieldCondition(
            key="metadata.source",
            match=models.MatchValue(value=named_source),
        )

        if query_filter is None:
            query_filter = models.Filter(
                must=[filename_condition]
            )
        else:
            # Preserve existing conditions and add the filename with AND.
            query_filter.must = [
                *(query_filter.must or []),
                filename_condition,
            ]


    client = get_qdrant_client()

    try:
        # Search should not silently create an empty collection.
        if not client.collection_exists(QDRANT_COLLECTION):
            raise ValueError(
                "The collection does not exist. Run ingestion first."
            )

        store = get_vector_store(client)

        # LangChain calls our embed_query() method and sends
        # the resulting query vector to Qdrant.
        matches = store.similarity_search_with_score(
            query=query,
            k=k,
            filter=query_filter,
        )

        results = []

        for rank, (document, score) in enumerate(matches, start=1):
            results.append(
                {
                    "rank": rank,
                    "score": float(score),
                    "page_content": document.page_content,
                    "metadata": dict(document.metadata),
                }
            )

        return results

    finally:
        client.close()



def product_maximum(field):
    """Calculate a maximum across all stored products.csv rows."""
    if field not in {"Sales_Units", "Rating"}:
        raise ValueError("Supported fields: Sales_Units and Rating.")

    client = get_qdrant_client()

    try:
        product_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="metadata.type",
                    match=models.MatchValue(value="csv"),
                ),
                models.FieldCondition(
                    key="metadata.source_path",
                    match=models.MatchValue(
                        value="excel/products.csv"
                    ),
                ),
                models.FieldCondition(
                    key="metadata.content_kind",
                    match=models.MatchValue(value="table_row"),
                ),
            ]
        )

        points = []
        offset = None

        # Read all matching records, not just the top search results.
        while True:
            batch, offset = client.scroll(
                collection_name=QDRANT_COLLECTION,
                scroll_filter=product_filter,
                limit=10,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            points.extend(batch)

            if offset is None:
                break

        if not points:
            raise ValueError("No product rows were found.")

        products = [
            point.payload["metadata"]
            for point in points
        ]

        product_ids = [
            product["row_data"]["Product_ID"]
            for product in products
        ]

        # Duplicate products could indicate obsolete ingestion records.
        if len(product_ids) != len(set(product_ids)):
            raise ValueError(
                "Duplicate product IDs found. Inspect stored rows."
            )

        maximum = max(
            product["row_data"][field]
            for product in products
        )

        # Return every winner if several products share the maximum.
        winners = [
            {
                "product": product["row_data"]["Product"],
                "product_id": product["row_data"]["Product_ID"],
                "value": product["row_data"][field],
                "source": product["source"],
                "source_path": product["source_path"],
                "row": product["row"],
            }
            for product in products
            if product["row_data"][field] == maximum
        ]

        winners.sort(key=lambda item: item["product_id"])

        return {
            "operation": "maximum",
            "field": field,
            "rows_checked": len(products),
            "maximum": maximum,
            "winners": winners,
        }

    finally:
        client.close()
