import json
from pathlib import Path

from langchain_core.documents import Document

from src.config import BASE_DIR


DATA_DIR = BASE_DIR / "data"

SUPPORTED_TYPES = {
    "pdf",
    "word",
    "csv",
    "excel",
    "image",
    "markdown",
    "html",
}


def create_document(text, source_type, file_path, **extra_metadata):
    """Create one LangChain Document with consistent source metadata."""

    text = text.strip()

    if not text:
        raise ValueError("Document text cannot be empty.")

    if source_type not in SUPPORTED_TYPES:
        raise ValueError(f"Unsupported source type: {source_type}")

    path = Path(file_path).resolve()

    if not path.is_file():
        raise FileNotFoundError(f"Source file does not exist: {path}")

    # Require source files to belong to this project's data directory.
    relative_path = path.relative_to(DATA_DIR.resolve())

    metadata = {
        "type": source_type,
        "source": path.name,
        "source_path": relative_path.as_posix(),
    }

    # Additional metadata must not replace the common source fields.
    conflicting_keys = metadata.keys() & extra_metadata.keys()

    if conflicting_keys:
        raise ValueError(
            f"Cannot replace source fields: {sorted(conflicting_keys)}"
        )

    metadata.update(extra_metadata)

    # Confirm metadata can be represented as standard JSON.
    json.dumps(metadata, allow_nan=False)

    return Document(
        page_content=text,
        metadata=metadata,
    )