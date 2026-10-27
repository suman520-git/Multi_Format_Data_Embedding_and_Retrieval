import math
from pathlib import Path

import pandas as pd
from langchain_community.document_loaders import DataFrameLoader

from src.document_utils import create_document


REQUIRED_COLUMNS = [
    "Product_ID",
    "Product",
    "Category",
    "Price_INR",
    "Sales_Units",
    "Rating",
]


def load_table_documents(file_path, sheet_name=None):
    """Load product rows from CSV or one explicitly named Excel sheet."""

    path = Path(file_path).resolve()

    if not path.is_file():
        raise FileNotFoundError(f"Table file does not exist: {path}")

    extension = path.suffix.lower()

    if extension == ".csv":
        if sheet_name is not None:
            raise ValueError("CSV files do not have worksheets.")

        source_type = "csv"

        # Keep blank records visible so validation does not silently skip them.
        frame = pd.read_csv(
            path,
            dtype=str,
            keep_default_na=False,
            skip_blank_lines=False,
            encoding="utf-8-sig",
        )

    elif extension == ".xlsx":
        if not isinstance(sheet_name, str) or not sheet_name.strip():
            raise ValueError("Provide the Excel worksheet name.")

        source_type = "excel"

        frame = pd.read_excel(
            path,
            sheet_name=sheet_name,
            dtype=str,
            keep_default_na=False,
            engine="openpyxl",
        )

    else:
        raise ValueError("Supported table formats are .csv and .xlsx.")

    missing_columns = set(REQUIRED_COLUMNS) - set(frame.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    if frame.empty:
        raise ValueError("The table contains no product rows.")

    prepared_rows = []
    seen_product_ids = set()

    for row_number, raw_row in enumerate(
        frame.to_dict(orient="records"),
        start=2,
    ):
        # Preserve all source columns, including any additional columns.
        row_data = {
            column: str(value).strip()
            for column, value in raw_row.items()
        }

        for column in REQUIRED_COLUMNS:
            if not row_data[column]:
                raise ValueError(
                    f"Empty {column} at row {row_number}."
                )

        product_id = row_data["Product_ID"]

        if product_id in seen_product_ids:
            raise ValueError(f"Duplicate Product_ID: {product_id}")

        seen_product_ids.add(product_id)

        try:
            price = float(row_data["Price_INR"])
            sales = float(row_data["Sales_Units"])
            rating = float(row_data["Rating"])
        except ValueError as error:
            raise ValueError(
                f"Invalid numeric value at row {row_number}."
            ) from error

        if not all(math.isfinite(value) for value in [price, sales, rating]):
            raise ValueError(f"Non-finite number at row {row_number}.")

        if price < 0 or sales < 0 or not sales.is_integer():
            raise ValueError(
                f"Price must be non-negative and sales must be "
                f"a non-negative whole number at row {row_number}."
            )

        if not 0 <= rating <= 5:
            raise ValueError(
                f"Rating must be between 0 and 5 at row {row_number}."
            )

        row_data["Price_INR"] = price
        row_data["Sales_Units"] = int(sales)
        row_data["Rating"] = rating

        text = (
            f"Product {row_data['Product']} belongs to "
            f"{row_data['Category']}.\n"
            f"Product ID is {product_id}.\n"
            f"Price is {price:g} INR.\n"
            f"Sales are {int(sales)} units.\n"
            f"Rating is {rating:g} out of 5."
        )

        prepared_rows.append(
            {
                "text": text,
                "row": row_number,
                "row_data": row_data,
            }
        )

    loader = DataFrameLoader(
        pd.DataFrame(prepared_rows),
        page_content_column="text",
    )

    documents = []

    for loaded_document in loader.load():
        extra_metadata = {}

        if source_type == "excel":
            extra_metadata["sheet"] = sheet_name

        document = create_document(
            text=loaded_document.page_content,
            source_type=source_type,
            file_path=path,
            content_kind="table_row",
            row=int(loaded_document.metadata["row"]),
            row_data=loaded_document.metadata["row_data"],
            **extra_metadata,
        )

        documents.append(document)

    return documents