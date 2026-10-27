import json

from src.config import BASE_DIR
from src.document_utils import DATA_DIR
from src.pdf_ingestion import load_pdf_text


def main():
    file_path = DATA_DIR / "pdf" / "operations_report.pdf"

    documents = load_pdf_text(file_path)

    print("Source:", file_path.name)
    print("Page documents:", len(documents))

    extracted_records = []

    for document in documents:
        print("\n" + "=" * 60)
        print("Page:", document.metadata["page"])
        print("Metadata:")
        print(json.dumps(document.metadata, indent=2))

        print("\nExtracted text:")
        print(document.page_content)

        extracted_records.append(
            {
                "page_content": document.page_content,
                "metadata": document.metadata,
            }
        )

    # These checks apply specifically to our known three-page sample.
    if len(documents) != 3:
        raise ValueError("Expected three pages in the sample PDF.")

    expected_facts = {
        1: ["Executive Summary", "420", "2 hours"],
        2: ["Department Training", "Engineering", "144"],
        3: ["Storage and Recovery", "11 PM IST", "30 days"],
    }

    for document in documents:
        page_number = document.metadata["page"]

        # Normalize whitespace for comparison only.
        searchable_text = " ".join(document.page_content.split())

        for expected_text in expected_facts[page_number]:
            if expected_text not in searchable_text:
                raise ValueError(
                    f"Missing expected text on page {page_number}: "
                    f"{expected_text}"
                )

    output_dir = BASE_DIR / "artifacts"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "pdf_text_extracted.json"
    output_path.write_text(
        json.dumps(extracted_records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nSaved extraction:", output_path)
    print("PDF text checks passed.")


if __name__ == "__main__":
    main()