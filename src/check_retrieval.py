import json
import math

from src.config import BASE_DIR
from src.retrieval import search


CHECKS = [
    {
        "query": "How many support tickets were resolved during the quarter?",
        "expected_type": "pdf",
    },
    {
        "query": "What should I start before running docker compose up -d?",
        "expected_type": "word",
    },
    {
        "query": "What are the price, sales, and rating of Laptop Alpha?",
        "expected_type": "csv",
    },
    {
        "query": "What does the Local Search Architecture diagram show?",
        "expected_type": "image",
    },
    {
        "query": "What are the customer support working hours?",
        "expected_type": "markdown",
    },
    {
        "query": "Within how many days can a customer return a product?",
        "expected_type": "html",
    },
    {
        "query": "Where do FastAPI and Qdrant run, and which ports do they use?",
        "expected_type": None,
    },
]


def main():
    saved_results = []
    target_hits = 0

    for check in CHECKS:
        query = check["query"]
        expected_type = check["expected_type"]

        print("\n" + "=" * 70)
        print("Question:", query)

        results = search(query, k=5)

        assert results, "Search returned no results."
        assert len(results) <= 5

        for result in results:
            assert math.isfinite(result["score"])
            assert result["page_content"].strip()
            assert result["metadata"]["source"]
            assert result["metadata"]["type"]

        returned_types = sorted({
            result["metadata"]["type"]
            for result in results
        })

        if expected_type is not None:
            target_found = expected_type in returned_types
            target_hits += int(target_found)

            print("Expected source type:", expected_type)
            print("Expected type found:", target_found)
        else:
            target_found = None

        print("Returned source types:", returned_types)

        for result in results:
            metadata = result["metadata"]

            print(
                f"\nRank {result['rank']} | "
                f"Score {result['score']:.4f} | "
                f"Type {metadata['type']} | "
                f"Source {metadata['source']}"
            )

            if "page" in metadata:
                print("Page:", metadata["page"])

            if "section" in metadata:
                print("Section:", metadata["section"])

            if "row" in metadata:
                print("Row:", metadata["row"])

            print(result["page_content"])

        saved_results.append(
            {
                "query": query,
                "expected_type": expected_type,
                "expected_type_found": target_found,
                "results": results,
            }
        )

    output_path = BASE_DIR / "artifacts" / "retrieval_checks.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(
            saved_results,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        ),
        encoding="utf-8",
    )

    print("\n--- Retrieval summary ---")
    print("Queries completed:", len(saved_results))
    print("Target source types found:", f"{target_hits}/6")
    print("Saved results:", output_path)
    print("Retrieval execution checks passed.")
    print("Review the returned evidence for relevance.")


if __name__ == "__main__":
    main()