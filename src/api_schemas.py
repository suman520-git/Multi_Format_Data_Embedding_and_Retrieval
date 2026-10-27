from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SourceType = Literal[
    "pdf",
    "word",
    "csv",
    "excel",
    "image",
    "markdown",
    "html",
]


class SearchRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    query: str = Field(
        min_length=1,
        max_length=2000,
    )

    k: int = Field(
        default=5,
        ge=1,
        le=20,
        strict=True,
    )

    source_type: SourceType | None = None

    source_path: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
    )

    page: int | None = Field(
        default=None,
        ge=1,
        strict=True,
    )


class AskRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    question: str = Field(
        min_length=1,
        max_length=2000,
    )

    k: int = Field(
        default=5,
        ge=1,
        le=20,
        strict=True,
    )

    source_type: SourceType | None = None

    source_path: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
    )

    page: int | None = Field(
        default=None,
        ge=1,
        strict=True,
    )


class ProductMaximumRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: Literal["Sales_Units", "Rating"]