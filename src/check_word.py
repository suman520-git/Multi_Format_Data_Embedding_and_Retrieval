import json
from collections import Counter

from src.config import BASE_DIR
from src.document_utils import DATA_DIR
from src.word_ingestion import load_word_documents


def main():
    file_path = DATA_DIR / "word" / "deployment_guide.docx"
    documents = load_word_documents(file_path)

    counts = Counter(
        document.metadata["content_kind"]
        for document in documents
    )

    print("Source:", file_path.name)
    print("Extracted records:", len(documents))
    print("Content kinds:", dict(counts))

    for document in documents:
        print("\n" + "=" * 60)
        print("Section:", document.metadata["section"])
        print("Kind:", document.metadata["content_kind"])
        print(document.page_content)

    headings = {
        document.page_content
        for document in documents
        if document.metadata["content_kind"] == "heading"
    }

    expected_headings = {
        "Local Development",
        "Starting the Application",
        "Persistent Storage",
        "Troubleshooting",
        "Service Reference",
    }

    missing_headings = expected_headings - headings

    if missing_headings:
        raise ValueError(
            f"Missing expected headings: {sorted(missing_headings)}"
        )

    tables = [
        document
        for document in documents
        if document.metadata["content_kind"] == "table"
    ]

    if len(tables) != 1:
        raise ValueError("Expected one service table in the sample Word file.")

    expected_rows = [
        ["Service", "Location", "Port"],
        ["FastAPI", "Windows host", "8000"],
        ["Qdrant", "Docker container", "6333"],
    ]

    if tables[0].metadata["table_rows"] != expected_rows:
        raise ValueError("The extracted service table does not match the sample.")

    startup_records = [
        document
        for document in documents
        if document.metadata["section"] == "Starting the Application"
        and document.metadata["content_kind"] == "text"
    ]

    startup_text = " ".join(
        document.page_content
        for document in startup_records
    )

    if "docker compose up -d" not in startup_text:
        raise ValueError("The startup instruction is missing from its section.")

    output_dir = BASE_DIR / "artifacts"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "word_extracted.json"

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
    print("Word extraction checks passed.")


if __name__ == "__main__":
    main()