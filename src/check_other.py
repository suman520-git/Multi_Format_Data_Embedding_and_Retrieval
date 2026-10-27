import json

from src.config import BASE_DIR
from src.other_ingestion import load_other_documents


def main():
    files = [
        BASE_DIR / "data" / "other" / "support_policy.md",
        BASE_DIR / "data" / "other" / "returns_policy.html",
    ]

    documents = []

    for path in files:
        documents.extend(load_other_documents(path))

    assert len(documents) == 2, "Expected two documents."

    by_type = {
        document.metadata["type"]: document
        for document in documents
    }

    assert set(by_type) == {"markdown", "html"}

    markdown_document = by_type["markdown"]
    html_document = by_type["html"]

    # Basic checks; review the printed text for factual completeness too.
    assert "#" in markdown_document.page_content
    assert "support" in markdown_document.page_content.lower()

    html_text = html_document.page_content.lower()

    assert html_document.metadata["table_count"] == 1
    assert "14" in html_text, "Return window was not found."
    assert "7" in html_text, "Refund processing period was not found."
    assert "seller" in html_text
    assert "customer" in html_text
    assert "console.log" not in html_text
    assert "this script is not policy content" not in html_text

    for document in documents:
        print("\n" + "=" * 60)
        print("Source:", document.metadata["source"])

        print("\nMetadata:")
        print(json.dumps(document.metadata, indent=2))

        print("\nExtracted content:")
        print(document.page_content)

    output_path = BASE_DIR / "artifacts" / "other_extracted.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

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

    print("\nOther-format documents:", len(documents))
    print("Saved extraction:", output_path)
    print("Markdown and HTML extraction checks passed.")


if __name__ == "__main__":
    main()