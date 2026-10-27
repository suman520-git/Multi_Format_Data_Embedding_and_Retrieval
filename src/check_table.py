import json

from src.config import BASE_DIR
from src.document_utils import DATA_DIR
from src.table_ingestion import load_table_documents


def main():
    file_path = DATA_DIR / "excel" / "products.csv"
    documents = load_table_documents(file_path)

    print("Source:", file_path.name)
    print("Product documents:", len(documents))

    if len(documents) != 30:
        raise ValueError("Expected 30 products in our sample CSV.")

    print("\nFirst product text:")
    print(documents[0].page_content)

    print("\nFirst product metadata:")
    print(json.dumps(documents[0].metadata, indent=2))

    # Inspect numeric values across all rows, without using similarity search.
    product_rows = [
        document.metadata["row_data"]
        for document in documents
    ]

    highest_sales = max(
        product_rows,
        key=lambda row: row["Sales_Units"],
    )

    highest_rating = max(
        product_rows,
        key=lambda row: row["Rating"],
    )

    if (
        highest_sales["Product"] != "Pen Smooth"
        or highest_sales["Sales_Units"] != 1500
    ):
        raise ValueError("Highest-sales result does not match our sample.")

    if (
        highest_rating["Product"] != "Chair Comfort"
        or highest_rating["Rating"] != 4.9
    ):
        raise ValueError("Highest-rating result does not match our sample.")

    print(
        "\nHighest sales:",
        highest_sales["Product"],
        highest_sales["Sales_Units"],
    )

    print(
        "Highest rating:",
        highest_rating["Product"],
        highest_rating["Rating"],
    )

    output_dir = BASE_DIR / "artifacts"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "table_extracted.json"

    records = [
        {
            "page_content": document.page_content,
            "metadata": document.metadata,
        }
        for document in documents
    ]

    output_path.write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nSaved extraction:", output_path)
    print("Table extraction checks passed.")


if __name__ == "__main__":
    main()