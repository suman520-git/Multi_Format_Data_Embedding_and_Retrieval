import logging

from fastapi import FastAPI, HTTPException

from src.config import APP_NAME, APP_ENV
from src.api_schemas import (
    SearchRequest,
    AskRequest,
    ProductMaximumRequest,
)
from src.retrieval import search
from src.answers import (
    answer_question,
    answer_product_maximum,
)


logger = logging.getLogger(__name__)

app = FastAPI(
    title=APP_NAME,
    version="0.1.0",
)


@app.get("/health")
def health():
    # This confirms the API is running.
    # It does not call Qdrant or either model provider.
    return {
        "status": "ok",
        "application": APP_NAME,
        "environment": APP_ENV,
    }


@app.post("/search")
def search_endpoint(request: SearchRequest):
    try:
        results = search(
            query=request.query,
            k=request.k,
            source_type=request.source_type,
            source_path=request.source_path,
            page=request.page,
        )

        return {
            "query": request.query,
            "count": len(results),
            "results": results,
        }

    except Exception:
        logger.exception("Search request failed.")

        raise HTTPException(
            status_code=500,
            detail="Search failed. Check the server terminal for details.",
        ) from None


@app.post("/ask")
def ask_endpoint(request: AskRequest):
    try:
        return answer_question(
            question=request.question,
            k=request.k,
            source_type=request.source_type,
            source_path=request.source_path,
            page=request.page,
        )

    except Exception:
        logger.exception("Answer request failed.")

        raise HTTPException(
            status_code=500,
            detail="Answer generation failed. Check the server terminal.",
        ) from None


@app.post("/products/maximum")
def product_maximum_endpoint(request: ProductMaximumRequest):
    try:
        return answer_product_maximum(request.field)

    except Exception:
        logger.exception("Product calculation failed.")

        raise HTTPException(
            status_code=500,
            detail="Product calculation failed. Check the server terminal.",
        ) from None