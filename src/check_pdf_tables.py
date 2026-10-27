import json
import re

from src.config import BASE_DIR
from src.document_utils import DATA_DIR
from src.pdf_ingestion import load_pdf_documents


def main():
    file_path = DATA_DIR / "pdf" / "operations_report.pdf"
    documents = load_pdf_documents(file_path)

    if len(documents) != 3:
        raise ValueError("Expected three pages in the sample PDF.")

    page_two = next(
        document
        for document in documents
        if document.metadata["page"] == 2
    )

    print("Page documents:", len(documents))
    print("\nPage 2 metadata:")
    print(json.dumps(page_two.metadata, indent=2))

    print("\nPage 2 extracted content:")
    print(page_two.page_content)

    # Read Markdown rows for inspection of this simple sample table.
    extracted_rows = []

    for line in page_two.page_content.splitlines():
        line = line.strip()

        if not line.startswith("|"):
            continue

        cells = [
            cell.strip()
            for cell in line.strip("|").split("|")
        ]

        # Ignore Markdown's separator row, such as |---|---|---|.
        if all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            continue

        extracted_rows.append(cells)

    expected_rows = [
        ["Department", "Employees", "Training Hours"],
        ["Engineering", "18", "144"],
        ["Sales", "12", "60"],
        ["Support", "10", "80"],
    ]

    for expected_row in expected_rows:
        if expected_row not in extracted_rows:
            raise ValueError(
                f"Missing or incorrectly extracted table row: "
                f"{expected_row}"
            )

    print("\nVerified table rows:")
    for row in expected_rows:
        print(row)

    records = [
        {
            "page_content": document.page_content,
            "metadata": document.metadata,
        }
        for document in documents
    ]

    output_dir = BASE_DIR / "artifacts"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "pdf_with_tables.json"
    output_path.write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nSaved extraction:", output_path)
    print("PDF table checks passed.")


if __name__ == "__main__":
    main()