from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader ,PyMuPDFLoader

from src.document_utils import create_document


def load_pdf_text(file_path):
    """Extract PDF text into one normalized Document per page."""

    path = Path(file_path).resolve()

    if not path.is_file():
        raise FileNotFoundError(f"PDF file does not exist: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError("Expected a PDF file.")

    loader = PyPDFLoader(
        file_path=str(path),
        mode="page",
    )

    loaded_pages = loader.load()

    if not loaded_pages:
        raise ValueError(f"No pages were loaded from: {path.name}")

    documents = []

    for loaded_page in loaded_pages:
        # Convert the loader's zero-based index to our one-based page number.
        page_number = loaded_page.metadata["page"] + 1
        text = loaded_page.page_content.strip()

        # Report missing text instead of silently losing a page.
        if not text:
            raise ValueError(
                f"No extractable text on page {page_number} "
                f"of {path.name}. Inspect the page; it may be blank "
                "or require OCR."
            )

        document = create_document(
            text=text,
            source_type="pdf",
            file_path=path,
            page=page_number,
            content_kind="text",
        )

        documents.append(document)

    return documents



def load_pdf_documents(file_path):
    """Extract PDF pages with detected tables represented as Markdown."""

    path = Path(file_path).resolve()

    if not path.is_file():
        raise FileNotFoundError(f"PDF file does not exist: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError("Expected a PDF file.")

    loader = PyMuPDFLoader(
        file_path=str(path),
        mode="page",
        extract_tables="markdown",
    )

    loaded_pages = loader.load()

    if not loaded_pages:
        raise ValueError(f"No pages were loaded from: {path.name}")

    documents = []

    for loaded_page in loaded_pages:
        page_number = loaded_page.metadata["page"] + 1
        text = loaded_page.page_content.strip()

        if not text:
            raise ValueError(
                f"No extractable text on page {page_number} "
                f"of {path.name}."
            )

        document = create_document(
            text=text,
            source_type="pdf",
            file_path=path,
            page=page_number,
            content_kind="page",
            extraction_method="pymupdf_markdown_tables",
        )

        documents.append(document)

    return documents