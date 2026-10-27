import json

from src.retrieval import search, product_maximum


def main():
    # Check that source and page restrictions are respected.
    results = search(
        "How many employees and training hours did Engineering have?",
        k=5,
        source_type="pdf",
        source_path="pdf/operations_report.pdf",
        page=2,
    )

    assert results

    for result in results:
        metadata = result["metadata"]

        assert metadata["type"] == "pdf"
        assert metadata["source_path"] == "pdf/operations_report.pdf"
        assert metadata["page"] == 2

    assert any(
        result["metadata"].get("row_data", {}).get("Department")
        == "Engineering"
        for result in results
    )

    print("--- Filtered PDF search ---")

    for result in results:
        print(
            f"\nRank: {result['rank']} | "
            f"Page: {result['metadata']['page']} | "
            f"Score: {result['score']:.4f}"
        )
        print(result["page_content"])

    # Our report has only three pages.
    missing_page = search(
        "What information is on page 7?",
        source_type="pdf",
        source_path="pdf/operations_report.pdf",
        page=7,
    )

    assert missing_page == []
    print("\nPage 7 results:", len(missing_page))

    sales = product_maximum("Sales_Units")
    rating = product_maximum("Rating")

    assert sales["rows_checked"] == 30
    assert rating["rows_checked"] == 30

    assert sales["maximum"] == 1500
    assert [
        winner["product"]
        for winner in sales["winners"]
    ] == ["Pen Smooth"]

    assert rating["maximum"] == 4.9
    assert [
        winner["product"]
        for winner in rating["winners"]
    ] == ["Chair Comfort"]

    print("\n--- Highest sales ---")
    print(json.dumps(sales, indent=2))

    print("\n--- Highest rating ---")
    print(json.dumps(rating, indent=2))

    print("\nMetadata filter and calculation checks passed.")


if __name__ == "__main__":
    main()