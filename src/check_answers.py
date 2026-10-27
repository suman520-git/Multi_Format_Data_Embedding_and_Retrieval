import json

from src.config import BASE_DIR
from src.answers import (
    answer_question,
    answer_product_maximum,
)


CASES = [
    {
        "question": "How many support tickets were resolved during the quarter?",
        "options": {},
        "expected": "420 tickets; citation to PDF page 1.",
    },
    {
        "question": "What does the Local Search Architecture diagram show?",
        "options": {
            "source_type": "image",
            "source_path": "images/architecture.png",
        },
        "expected": "User, FastAPI on Windows port 8000, Qdrant in Docker port 6333.",
    },
    {
        "question": "Who pays return shipping for a defective product?",
        "options": {
            "source_type": "html",
        },
        "expected": "Seller; citation to the return shipping section.",
    },
    {
        "question": "What is the CEO's personal phone number?",
        "options": {},
        "expected": "Abstain: the dataset does not provide this information.",
    },
    {
        "question": "What information is on page 7 of the report?",
        "options": {
            "source_type": "pdf",
            "source_path": "pdf/operations_report.pdf",
            "page": 7,
        },
        "expected": "Abstain: no matching page was retrieved.",
    },
]


def main():
    records = []

    for case in CASES:
        result = answer_question(
            case["question"],
            **case["options"],
        )

        assert result["answer"].strip()

        if result["abstained"]:
            assert result["citations"] == []
        else:
            assert result["citations"]

        print("\n" + "=" * 70)
        print("Question:", case["question"])
        print("Expected behavior:", case["expected"])
        print("Answer:", result["answer"])
        print("Abstained:", result["abstained"])
        print("Citations:")
        print(json.dumps(result["citations"], indent=2))

        records.append({
            "expected": case["expected"],
            "result": result,
        })

    for field in ["Sales_Units", "Rating"]:
        result = answer_product_maximum(field)

        assert result["calculation"]["rows_checked"] == 30

        print("\n" + "=" * 70)
        print("Calculation:", field)
        print("Answer:", result["answer"])
        print("Citations:")
        print(json.dumps(result["citations"], indent=2))

        records.append({
            "field": field,
            "result": result,
        })

    output_path = BASE_DIR / "artifacts" / "answer_checks.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(
            records,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        ),
        encoding="utf-8",
    )

    print("\nCases completed:", len(records))
    print("Saved answers:", output_path)
    print("Answer execution checks passed.")
    print("Review factual accuracy, citations, and abstentions.")


if __name__ == "__main__":
    main()