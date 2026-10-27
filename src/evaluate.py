import json
from collections import Counter
from datetime import datetime, timezone

from src.config import BASE_DIR
from src.answers import answer_question, answer_product_maximum


def question_case(
    case_id,
    category,
    question,
    expected,
    source_path=None,
    locator=None,
    options=None,
    field=None,
    maximum=None,
    product=None,
    abstain=False,
):
    """Describe one test without sending its expected answer to the model."""
    return {
        "id": case_id,
        "category": category,
        "question": question,
        "expected": expected,
        "source_path": source_path,
        "locator": locator or {},
        "options": options or {},
        "field": field,
        "maximum": maximum,
        "product": product,
        "expect_abstention": abstain,
    }


CASES = [
    question_case(
        "Q01", "pdf",
        "How many support tickets were resolved during the quarter?",
        "420 tickets.",
        "pdf/operations_report.pdf",
        locator={"page": 1},
    ),
    question_case(
        "Q02", "pdf",
        "How many employees and training hours did Engineering have?",
        "18 employees and 144 training hours.",
        "pdf/operations_report.pdf",
        locator={
            "page": 2,
            "row_data": {
                "Department": "Engineering",
                "Employees": "18",
                "Training Hours": "144",
            },
        },
    ),
    question_case(
        "Q03", "pdf",
        "When are database backups scheduled and how long are they retained?",
        "Daily at 11 PM IST; retained for 30 days.",
        "pdf/operations_report.pdf",
        locator={"page": 3},
    ),
    question_case(
        "Q04", "word",
        "What should I start before running docker compose up -d?",
        "Start Docker Desktop.",
        "word/deployment_guide.docx",
        locator={"section": "Starting the Application"},
    ),
    question_case(
        "Q05", "word",
        "Does the Qdrant Docker named volume count as a backup?",
        "No. It provides persistent storage but is not a backup.",
        "word/deployment_guide.docx",
        locator={"section": "Persistent Storage"},
    ),
    question_case(
        "Q06", "word",
        "What should I check if the API cannot reach Qdrant?",
        "Check the container status and configured QDRANT_URL.",
        "word/deployment_guide.docx",
        locator={"section": "Troubleshooting"},
    ),
    question_case(
        "Q07", "csv",
        "What are the price, sales, and rating of Laptop Alpha?",
        "75000 INR; 230 units; rating 4.5 out of 5.",
        "excel/products.csv",
        locator={"row": 2},
    ),
    question_case(
        "Q08", "calculation",
        "Which product has the highest sales across all products?",
        "Pen Smooth, 1500 units, across 30 product rows.",
        "excel/products.csv",
        locator={"row": 28},
        field="Sales_Units",
        maximum=1500,
        product="Pen Smooth",
    ),
    question_case(
        "Q09", "calculation",
        "Which product has the highest rating across all products?",
        "Chair Comfort, 4.9 out of 5, across 30 product rows.",
        "excel/products.csv",
        locator={"row": 18},
        field="Rating",
        maximum=4.9,
        product="Chair Comfort",
    ),
    question_case(
        "Q10", "image",
        "What does the Local Search Architecture diagram show?",
        "User sends requests to FastAPI on Windows port 8000; "
        "FastAPI searches Qdrant in Docker on port 6333.",
        "images/architecture.png",
    ),
    question_case(
        "Q11", "image",
        "What sequence does the Docker Application Deployment diagram show?",
        "Source code and Dockerfile -> Docker image -> running container; "
        "docker build followed by docker run. The current FastAPI app "
        "still runs directly on Windows.",
        "images/deployment_flow.png",
    ),
    question_case(
        "Q12", "image",
        "In the Product Sales Comparison chart, which of the three "
        "displayed products has the highest sales?",
        "Keyboard Swift, 480 units, among the three displayed products.",
        "images/sales_chart.png",
    ),
    question_case(
        "Q13", "image",
        "What does the product_laptop.png photograph show?",
        "An open silver laptop with a blue screen on a light gray surface.",
        "images/product_laptop.png",
    ),
    question_case(
        "Q14", "image",
        "What furniture and equipment appear in office_workspace.png?",
        "A desk, office chair, monitor, keyboard, mouse, and desk lamp.",
        "images/office_workspace.png",
    ),
    question_case(
        "Q15", "markdown",
        "What are the customer support working hours?",
        "Monday to Friday, 9 AM to 6 PM IST.",
        "other/support_policy.md",
        locator={
            "section": "Customer Support Policy > Support Hours"
        },
    ),
    question_case(
        "Q16", "markdown",
        "When are unresolved critical issues escalated, and to whom?",
        "After 2 hours, to the support manager.",
        "other/support_policy.md",
        locator={
            "section": "Customer Support Policy > Escalation"
        },
    ),
    question_case(
        "Q17", "html",
        "Within how many days of delivery can a product be returned?",
        "Within 14 days of delivery.",
        "other/returns_policy.html",
        locator={
            "section": "Product Returns Policy > Return Window"
        },
    ),
    question_case(
        "Q18", "html",
        "Who pays return shipping when the customer changes their mind?",
        "The customer.",
        "other/returns_policy.html",
        locator={
            "section": "Product Returns Policy > Return Shipping"
        },
    ),
    question_case(
        "Q19", "missing_information",
        "What is the CEO's personal phone number?",
        "Abstain: this information is not in the dataset.",
        abstain=True,
    ),
    question_case(
        "Q20", "missing_information",
        "What information is on page 7 of the report?",
        "Abstain: the report has only three pages.",
        options={
            "source_type": "pdf",
            "source_path": "pdf/operations_report.pdf",
            "page": 7,
        },
        abstain=True,
    ),
]


def matches_expected_source(metadata, case):
    """Match a source and its expected page, section, or row."""
    if metadata.get("source_path") != case["source_path"]:
        return False

    return all(
        metadata.get(key) == value
        for key, value in case["locator"].items()
    )


def inspect_result(case, result):
    """Run structural checks, not semantic grading of answer text."""
    checks = {
        "abstention_matches": (
            result["abstained"] == case["expect_abstention"]
        ),
        "citation_structure_ok": (
            not result["citations"]
            if result["abstained"]
            else bool(result["citations"])
        ),
    }

    if case["expect_abstention"]:
        return checks

    citation_metadata = [
        citation.get("metadata", citation)
        for citation in result["citations"]
    ]

    checks["expected_citation_found"] = any(
        matches_expected_source(metadata, case)
        for metadata in citation_metadata
    )

    if case["field"] is not None:
        calculation = result["calculation"]

        checks["exact_calculation_correct"] = (
            calculation["rows_checked"] == 30
            and calculation["maximum"] == case["maximum"]
            and sorted(
                winner["product"]
                for winner in calculation["winners"]
            ) == [case["product"]]
        )

    else:
        checks["expected_evidence_retrieved"] = any(
            matches_expected_source(item["metadata"], case)
            for item in result["retrieved"]
        )

    return checks


def main():
    assert len(CASES) == 20
    assert len({case["question"] for case in CASES}) == 20

    # Keep separate outputs for each run instead of overwriting evidence.
    run_id = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S%fZ"
    )

    output_dir = BASE_DIR / "artifacts" / "evaluation" / run_id
    output_dir.mkdir(parents=True, exist_ok=False)

    records = []

    for case in CASES:
        print(f"\n{case['id']}: {case['question']}")

        try:
            if case["field"] is not None:
                # Explicit operation selection; this is not an
                # automatic natural-language routing test.
                result = answer_product_maximum(case["field"])
            else:
                # Only the question and explicit request options are
                # sent to the application. Expected answers stay here.
                result = answer_question(
                    case["question"],
                    **case["options"],
                )

            checks = inspect_result(case, result)

            record = {
                "case": case,
                "result": result,
                "checks": checks,
                "automatic_checks_passed": all(checks.values()),
                "error": None,
                "manual_review": "pending",
            }

            print("Answer:", result["answer"])
            print("Checks:", checks)

        except Exception as error:
            # Keep failures and continue so we can inspect the full run.
            record = {
                "case": case,
                "result": None,
                "checks": {},
                "automatic_checks_passed": False,
                "error": f"{type(error).__name__}: {error}",
                "manual_review": "pending",
            }

            print("ERROR:", record["error"])

        records.append(record)

        # Save after each question in case the run is interrupted.
        (output_dir / "results.json").write_text(
            json.dumps(records, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    flagged = [
        record["case"]["id"]
        for record in records
        if not record["automatic_checks_passed"]
    ]

    summary = {
        "questions": len(CASES),
        "completed_without_error": sum(
            record["error"] is None
            for record in records
        ),
        "request_or_processing_errors": sum(
            record["error"] is not None
            for record in records
        ),
        "automatic_checks_passed": sum(
            record["automatic_checks_passed"]
            for record in records
        ),
        "flagged_cases": flagged,
        "questions_by_category": dict(Counter(
            case["category"] for case in CASES
        )),
        "manual_answer_review": "pending",
    }

    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    # Produce a readable review sheet alongside the full JSON.
    review_lines = []

    for record in records:
        case = record["case"]

        review_lines.extend([
            "=" * 70,
            f"{case['id']} | {case['category']}",
            f"Question: {case['question']}",
            f"Expected: {case['expected']}",
        ])

        if record["error"]:
            review_lines.append(f"Error: {record['error']}")
        else:
            result = record["result"]

            review_lines.extend([
                f"Actual: {result['answer']}",
                f"Abstained: {result['abstained']}",
                "Citations: " + json.dumps(
                    result["citations"],
                    ensure_ascii=False,
                ),
                "Checks: " + json.dumps(record["checks"]),
            ])

        review_lines.extend([
            "Manual review: pending",
            "",
        ])

    (output_dir / "review.txt").write_text(
        "\n".join(review_lines),
        encoding="utf-8",
    )

    print("\n--- Evaluation summary ---")
    print(json.dumps(summary, indent=2))
    print("Saved evaluation:", output_dir)
    print("Automatic checks are not a factual-accuracy score.")


if __name__ == "__main__":
    main()