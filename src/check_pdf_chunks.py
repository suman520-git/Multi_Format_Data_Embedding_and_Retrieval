import json
from collections import Counter

from src.config import BASE_DIR
from src.pdf_ingestion import load_pdf_documents
from src.chunking import chunk_pdf_documents


def main():
    path = BASE_DIR / "data" / "pdf" / "operations_report.pdf"

    page_documents = load_pdf_documents(path)
    chunks = chunk_pdf_documents(page_documents)

    counts = Counter(
        chunk.metadata["content_kind"]
        for chunk in chunks
    )

    print("PDF pages:", len(page_documents))
    print("PDF chunks:", len(chunks))
    print("Content kinds:", dict(counts))

    table_chunks = [
        chunk
        for chunk in chunks
        if chunk.metadata["content_kind"] == "table_row"
    ]

    expected_rows = [
        {
            "Department": "Engineering",
            "Employees": "18",
            "Training Hours": "144",
        },
        {
            "Department": "Sales",
            "Employees": "12",
            "Training Hours": "60",
        },
        {
            "Department": "Support",
            "Employees": "10",
            "Training Hours": "80",
        },
    ]

    assert [c.metadata["row_data"] for c in table_chunks] == expected_rows
    assert all(c.metadata["page"] == 2 for c in table_chunks)

    page_two_text = "\n".join(
        chunk.page_content
        for chunk in chunks
        if chunk.metadata["page"] == 2
        and chunk.metadata["content_kind"] == "text"
    )

    # Confirm the narrative survived and table values are no longer
    # duplicated inside the narrative chunks.
    assert "Department Training" in page_two_text
    assert "following table" in page_two_text.lower()
    assert "Engineering" not in page_two_text
    assert "144" not in page_two_text

    all_text = " ".join(
        " ".join(chunk.page_content.split())
        for chunk in chunks
    )

    assert "420" in all_text
    assert "11 PM IST" in all_text
    assert "30 days" in all_text

    for chunk in chunks:
        assert chunk.page_content.strip()

        if chunk.metadata["page"] == 2:
            print("\n" + "=" * 60)
            print(json.dumps(chunk.metadata, indent=2))
            print(chunk.page_content)

    output_path = BASE_DIR / "artifacts" / "pdf_chunks.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(
            [
                {
                    "page_content": chunk.page_content,
                    "metadata": chunk.metadata,
                }
                for chunk in chunks
            ],
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("\nSaved chunks:", output_path)
    print("PDF chunk checks passed.")


if __name__ == "__main__":
    main()