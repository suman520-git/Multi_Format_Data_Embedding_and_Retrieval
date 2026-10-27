import json

from src.document_utils import DATA_DIR, create_document


def main():
    # Manually supplied text for checking the shared record structure.
    # PDF extraction will be implemented in the next step.
    document = create_document(
        text="The support team resolved 420 tickets.",
        source_type="pdf",
        file_path=DATA_DIR / "pdf" / "operations_report.pdf",
        page=1,
        content_kind="text",
    )

    print("Text:")
    print(document.page_content)

    print("\nMetadata:")
    print(json.dumps(document.metadata, indent=2))

    print("\nDocument structure check passed.")


if __name__ == "__main__":
    main()