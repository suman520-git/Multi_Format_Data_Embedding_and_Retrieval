import re

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_text_splitters import MarkdownHeaderTextSplitter



TEXT_CHUNK_SIZE = 600
TEXT_CHUNK_OVERLAP = 80


def separate_pdf_table(text):
    """Separate the simple Markdown table in our sample PDF."""
    lines = text.splitlines()

    # Locate Markdown table lines produced by our PDF loader.
    table_positions = [
        index
        for index, line in enumerate(lines)
        if line.strip().startswith("|")
        and line.strip().endswith("|")
    ]

    if not table_positions:
        return text, []

    # This version supports one continuous table per page.
    first = table_positions[0]
    last = table_positions[-1]

    if table_positions != list(range(first, last + 1)):
        raise ValueError(
            "Multiple or interrupted tables need additional handling."
        )

    rows = []

    for index in table_positions:
        cells = [
            cell.strip()
            for cell in lines[index].strip().strip("|").split("|")
        ]

        # Ignore Markdown's separator row: |---|---|---|
        if all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            continue

        rows.append(cells)

    if len(rows) < 2:
        raise ValueError("Expected table headers and at least one data row.")

    headers = rows[0]

    if not all(headers) or len(set(headers)) != len(headers):
        raise ValueError("Table headers must be nonempty and unique.")

    if any(len(row) != len(headers) for row in rows[1:]):
        raise ValueError("Table rows do not match the header width.")

    # Remove the Markdown table from the narrative.
    narrative_lines = lines[:first] + lines[last + 1:]

    # Our PDF loader also extracted each table cell on its own line.
    # Look for that complete sequence, rather than deleting individual
    # numbers or department names wherever they appear.
    flattened_cells = [
        cell
        for row in rows
        for cell in row
    ]

    nonempty_lines = [
        line.strip()
        for line in narrative_lines
        if line.strip()
    ]

    width = len(flattened_cells)

    matches = [
        index
        for index in range(len(nonempty_lines) - width + 1)
        if nonempty_lines[index:index + width] == flattened_cells
    ]

    # Stop if extraction changes instead of deleting uncertain content.
    if len(matches) != 1:
        raise ValueError(
            "Expected exactly one duplicate plain-text table. "
            "Inspect the PDF extraction before continuing."
        )

    start = matches[0]
    del nonempty_lines[start:start + width]

    narrative = "\n".join(nonempty_lines)

    return narrative, rows


def chunk_pdf_documents(page_documents):
    """Create text chunks and complete table-row chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=TEXT_CHUNK_SIZE,
        chunk_overlap=TEXT_CHUNK_OVERLAP,
        length_function=len,
    )

    chunks = []

    for page_document in page_documents:
        if page_document.metadata["type"] != "pdf":
            raise ValueError("This function accepts PDF documents only.")

        narrative, table_rows = separate_pdf_table(
            page_document.page_content
        )

        page_chunks = []

        if narrative.strip():
            text_document = Document(
                page_content=narrative,
                metadata={
                    **page_document.metadata,
                    "content_kind": "text",
                    "chunk_strategy": "recursive_characters",
                },
            )

            page_chunks.extend(
                splitter.split_documents([text_document])
            )

        if table_rows:
            headers = table_rows[0]

            # The first nonempty narrative line is our sample page heading.
            # This assumption is specific to the current PDF layout.
            section = (
                narrative.splitlines()[0]
                if narrative.strip()
                else "Table"
            )

            for row_number, values in enumerate(
                table_rows[1:], start=2
            ):
                row_data = dict(zip(headers, values))

                row_text = "; ".join(
                    f"{header}: {value}"
                    for header, value in row_data.items()
                ) + "."

                page_chunks.append(
                    Document(
                        page_content=f"{section}\n{row_text}",
                        metadata={
                            **page_document.metadata,
                            "content_kind": "table_row",
                            "chunk_strategy": "complete_table_row",
                            "section": section,
                            "table_index": 1,
                            "table_row": row_number,
                            "row_data": row_data,
                        },
                    )
                )

        # Index chunks within each source page, starting at zero.
        for chunk_index, chunk in enumerate(page_chunks):
            chunk.metadata["chunk_index"] = chunk_index

        chunks.extend(page_chunks)

    return chunks



def chunk_word_documents(documents):
    """Attach section context to paragraphs and preserve small tables."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=TEXT_CHUNK_SIZE,
        chunk_overlap=TEXT_CHUNK_OVERLAP,
        length_function=len,
    )

    chunks = []

    for document in documents:
        kind = document.metadata["content_kind"]

        # Heading text is already stored in the following records'
        # section metadata, so avoid standalone heading-only chunks.
        if kind == "heading":
            continue

        section = document.metadata.get("section", "Document")
        metadata = dict(document.metadata)

        if kind == "table":
            # Our service table is small enough to keep complete.
            metadata["chunk_strategy"] = "complete_table"

            chunks.append(
                Document(
                    page_content=(
                        f"{section}\n{document.page_content}"
                    ),
                    metadata=metadata,
                )
            )

        elif kind == "text":
            metadata["chunk_strategy"] = "paragraph_with_section"

            # Split the paragraph first, then attach its section heading
            # to every resulting piece.
            for piece in splitter.split_text(document.page_content):
                chunks.append(
                    Document(
                        page_content=f"{section}\n{piece}",
                        metadata=dict(metadata),
                    )
                )

        else:
            raise ValueError(f"Unexpected Word content kind: {kind}")

    return chunks


def chunk_policy_documents(documents):
    """Split normalized Markdown and HTML by their heading structure."""
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "heading_1"),
            ("##", "heading_2"),
            ("###", "heading_3"),
            ("####", "heading_4"),
            ("#####", "heading_5"),
            ("######", "heading_6"),
        ],
        strip_headers=True,
    )

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=TEXT_CHUNK_SIZE,
        chunk_overlap=TEXT_CHUNK_OVERLAP,
        length_function=len,
    )

    chunks = []

    for document in documents:
        sections = header_splitter.split_text(
            document.page_content
        )

        for section in sections:
            # Build a readable hierarchy, such as:
            # Product Returns Policy > Return Window
            heading_values = [
                section.metadata[f"heading_{level}"]
                for level in range(1, 7)
                if f"heading_{level}" in section.metadata
            ]

            section_path = " > ".join(heading_values)

            metadata = {
                **document.metadata,
                **section.metadata,
                "content_kind": "section",
                "section": section_path,
                "chunk_strategy": "headings_then_characters",
            }

            for piece in text_splitter.split_text(
                section.page_content
            ):
                text = (
                    f"{section_path}\n{piece}"
                    if section_path
                    else piece
                )

                chunks.append(
                    Document(
                        page_content=text,
                        metadata=dict(metadata),
                    )
                )

    return chunks


def keep_complete_documents(documents, strategy):
    """Keep already meaningful units such as product rows intact."""
    return [
        Document(
            page_content=document.page_content,
            metadata={
                **document.metadata,
                "chunk_strategy": strategy,
            },
        )
        for document in documents
    ]