import json

from src.config import BASE_DIR
from src.document_utils import DATA_DIR
from src.image_ingestion import load_image_document


EXPECTED_IMAGES = [
    "architecture.png",
    "deployment_flow.png",
    "sales_chart.png",
    "product_laptop.png",
    "office_workspace.png",
]


def main():
    image_dir = DATA_DIR / "images"

    # Check all filenames before making any model requests.
    missing_files = [
        name
        for name in EXPECTED_IMAGES
        if not (image_dir / name).is_file()
    ]

    if missing_files:
        raise FileNotFoundError(
            f"Missing expected images: {missing_files}"
        )

    documents = []

    for name in EXPECTED_IMAGES:
        document = load_image_document(image_dir / name)
        documents.append(document)

        print("\n" + "=" * 60)
        print("Source:", document.metadata["source"])
        print("Review status:", document.metadata["review_status"])
        print("Description:")
        print(document.page_content)

    output_dir = BASE_DIR / "artifacts"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "images_described.json"

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

    print("\nImage documents:", len(documents))
    print("Saved descriptions:", output_path)
    print("Image processing completed. Visual review is still required.")


if __name__ == "__main__":
    main()