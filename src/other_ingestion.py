from pathlib import Path

from bs4 import BeautifulSoup
from langchain_community.document_loaders import TextLoader

from src.document_utils import create_document


def load_other_documents(file_path):
    """Load one Markdown or simple HTML file as a Document."""
    path = Path(file_path).resolve()

    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = path.suffix.lower()

    if suffix not in {".md", ".html", ".htm"}:
        raise ValueError("Expected a Markdown or HTML file.")

    # Read the file through a LangChain loader.
    loaded = TextLoader(
        str(path),
        encoding="utf-8-sig",
    ).load()

    text = loaded[0].page_content
    extra_metadata = {}

    if suffix == ".md":
        # Preserve Markdown headings and other formatting for later chunking.
        source_type = "markdown"
        extraction_method = "text_loader"

    else:
        source_type = "html"
        extraction_method = "beautifulsoup_table_aware"

        soup = BeautifulSoup(text, "html.parser")

        # Keep the HTML page title as metadata.
        title = (
            soup.title.get_text(" ", strip=True)
            if soup.title
            else path.stem
        )

        # These elements are not policy content.
        for element in soup.find_all(
            ["script", "style", "noscript", "template"]
        ):
            element.decompose()

        # Use the body when present so head metadata is excluded.
        body = soup.body if soup.body is not None else soup

        table_count = 0

        for table in body.find_all("table"):
            # This parser supports simple rectangular tables.
            # Stop explicitly if a table needs more complex handling.
            if table.find("table") is not None:
                raise ValueError("Nested HTML tables are not supported.")

            for cell in table.find_all(["th", "td"]):
                if (
                    cell.get("rowspan", "1") != "1"
                    or cell.get("colspan", "1") != "1"
                ):
                    raise ValueError(
                        "Merged HTML table cells need special handling."
                    )

            rows = []

            for tr in table.find_all("tr"):
                cells = [
                    cell.get_text(" ", strip=True)
                    for cell in tr.find_all(["th", "td"])
                ]

                if cells:
                    rows.append(cells)

            if len(rows) < 2:
                raise ValueError(
                    "Expected a header and at least one HTML data row."
                )

            headers = rows[0]

            if not all(headers) or len(set(headers)) != len(headers):
                raise ValueError(
                    "HTML table headers must be nonempty and unique."
                )

            row_sentences = []

            for values in rows[1:]:
                if len(values) != len(headers):
                    raise ValueError(
                        "HTML table row length does not match its headers."
                    )

                # Keep each cell associated with its column name.
                sentence = "; ".join(
                    f"{header}: {value}"
                    for header, value in zip(headers, values)
                )

                row_sentences.append(sentence + ".")

            # Preserve a caption if the table has one.
            caption = table.find("caption")
            if caption is not None:
                row_sentences.insert(
                    0, caption.get_text(" ", strip=True)
                )

            replacement = soup.new_tag("p")
            replacement.string = "\n".join(row_sentences)

            # Replace the original table to avoid duplicate table text.
            table.replace_with(replacement)
            table_count += 1

        # Convert HTML headings into recognizable Markdown-style headings.
        for heading in body.find_all(
            ["h1", "h2", "h3", "h4", "h5", "h6"]
        ):
            level = int(heading.name[1])
            heading_text = heading.get_text(" ", strip=True)
            heading.replace_with(
                f"\n{'#' * level} {heading_text}\n"
            )

        text = body.get_text("\n", strip=True)

        extra_metadata = {
            "title": title,
            "table_count": table_count,
        }

    document = create_document(
        text=text,
        source_type=source_type,
        file_path=path,
        content_kind="document",
        extraction_method=extraction_method,
        **extra_metadata,
    )

    return [document]