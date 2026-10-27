from pathlib import Path

from bs4 import BeautifulSoup
from langchain_community.document_loaders import (
    UnstructuredWordDocumentLoader,
)

from src.document_utils import create_document


def table_html_to_text(html):
    """Convert a simple table into text that repeats its column headings."""

    soup = BeautifulSoup(html, "html.parser")
    rows = []

    for table_row in soup.find_all("tr"):
        cells = [
            cell.get_text(" ", strip=True)
            for cell in table_row.find_all(["th", "td"])
        ]

        if cells:
            rows.append(cells)

    if len(rows) < 2:
        raise ValueError("Expected a table header and at least one data row.")

    # Our sample table has one header row and no merged cells.
    headers = rows[0]

    if any(not header for header in headers):
        raise ValueError("The table contains an empty column heading.")

    if len(set(headers)) != len(headers):
        raise ValueError("The table contains duplicate column headings.")

    sentences = []

    for row in rows[1:]:
        if len(row) != len(headers):
            raise ValueError("Table row does not match the header columns.")

        fields = [
            f"{header}: {value}"
            for header, value in zip(headers, row)
        ]

        sentences.append("; ".join(fields) + ".")

    return "\n".join(sentences), rows


def load_word_documents(file_path):
    """Load Word elements and attach consistent source metadata."""

    path = Path(file_path).resolve()

    if not path.is_file():
        raise FileNotFoundError(f"Word file does not exist: {path}")

    if path.suffix.lower() != ".docx":
        raise ValueError("Expected a .docx file.")

    loader = UnstructuredWordDocumentLoader(
        str(path),
        mode="elements",
    )

    elements = loader.load()

    documents = []
    current_section = "Document introduction"

    for element_index, element in enumerate(elements, start=1):
        text = element.page_content.strip()

        if not text:
            continue

        category = element.metadata.get("category", "Uncategorized")
        extra_metadata = {}

        if category == "Title":
            current_section = text
            content_kind = "heading"

        elif category == "Table":
            content_kind = "table"
            html = element.metadata.get("text_as_html")

            if not html:
                raise ValueError(
                    "A Word table was detected without structured HTML."
                )

            text, table_rows = table_html_to_text(html)
            extra_metadata["table_rows"] = table_rows

        else:
            content_kind = "text"

        document = create_document(
            text=text,
            source_type="word",
            file_path=path,
            section=current_section,
            content_kind=content_kind,
            element_index=element_index,
            element_category=category,
            **extra_metadata,
        )

        documents.append(document)

    if not documents:
        raise ValueError(f"No content extracted from: {path.name}")

    return documents