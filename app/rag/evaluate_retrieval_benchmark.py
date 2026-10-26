import json
from pathlib import Path
from datetime import datetime, timezone

from app.rag.retriever import get_retriever


# ============================================================
# CONFIGURATION
# ============================================================

REPORT_DIR = Path("reports")
REPORT_PATH = REPORT_DIR / "retrieval_benchmark.json"

# required_sources:
# Documents that must be retrieved.
#
# acceptable_sources:
# Additional documents that may provide useful context.
#
# For unanswerable questions, both lists must be empty.

TEST_CASES = [
    {
        "question": "Explain reinforcement learning using ml_notes.txt",
        "required_sources": ["ml_notes.txt"],
        "acceptable_sources": [],
    },
    {
        "question": "What is deep learning?",
        "required_sources": ["dl_notes.txt"],
        "acceptable_sources": ["ai_notes.txt"],
    },
    {
        "question": (
            "Compare machine learning, deep learning, "
            "and artificial intelligence"
        ),
        "required_sources": [
            "ai_notes.txt",
            "dl_notes.txt",
            "ml_notes.txt",
        ],
        "acceptable_sources": [],
    },
    {
        "question": "What is machine learning?",
        "required_sources": ["ai_notes.txt", "ml_notes.txt"],
        "acceptable_sources": ["dl_notes.txt"],
    },
    {
        "question": (
            "What is the difference between supervised "
            "and unsupervised learning?"
        ),
        "required_sources": ["ml_notes.txt"],
        "acceptable_sources": [],
    },
    {
        "question": "What are CNN and RNN used for?",
        "required_sources": ["dl_notes.txt"],
        "acceptable_sources": [],
    },
    {
        "question": "What does LSTM handle?",
        "required_sources": ["dl_notes.txt"],
        "acceptable_sources": [],
    },
    {
        "question": "What is artificial intelligence?",
        "required_sources": ["ai_notes.txt"],
        "acceptable_sources": ["ml_notes.txt"],
    },
    {
        "question": "Explain quantum computing.",
        "required_sources": [],
        "acceptable_sources": [],
    },
    {
        "question": "Explain photosynthesis in plants.",
        "required_sources": [],
        "acceptable_sources": [],
    },
    {
        "question": "Who won the 2022 FIFA World Cup?",
        "required_sources": [],
        "acceptable_sources": [],
    },
    {
        "question": "What is the capital of Japan?",
        "required_sources": [],
        "acceptable_sources": [],
    },
]


# ============================================================
# HELPERS
# ============================================================

def get_source_name(document):
    """Return the source filename from document metadata."""
    metadata = getattr(document, "metadata", {}) or {}
    source = metadata.get("source") or metadata.get("filename")

    if not source:
        return None

    return Path(str(source)).name


def calculate_source_metrics(required_sources, actual_sources):
    """Calculate retrieval metrics against required sources."""
    required = set(required_sources)
    actual = set(actual_sources)

    true_positives = len(required & actual)

    precision = (
        true_positives / len(actual)
        if actual
        else 0.0
    )

    recall = (
        true_positives / len(required)
        if required
        else 1.0
    )

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall > 0
        else 0.0
    )

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def retrieve_documents(retriever, question):
    """Support invoke() and get_relevant_documents()."""
    if hasattr(retriever, "invoke"):
        return retriever.invoke(question)

    if hasattr(retriever, "get_relevant_documents"):
        return retriever.get_relevant_documents(question)

    raise TypeError(
        "Retriever has neither invoke() nor get_relevant_documents()."
    )


# ============================================================
# BENCHMARK
# ============================================================

def main():
    print("=" * 70)
    print("RAG RETRIEVAL-ONLY BENCHMARK")
    print("=" * 70)
    print("LLM answer generation: DISABLED")
    print("LLM judge: DISABLED")
    print("Embedding API may still be used.")
    print()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    answerable_metrics = []

    answerable_passes = 0
    answerable_total = 0

    unanswerable_correct = 0
    unanswerable_total = 0

    errors = 0

    for index, case in enumerate(TEST_CASES, start=1):
        question = case["question"]
        required_sources = case["required_sources"]
        acceptable_sources = case["acceptable_sources"]

        allowed_sources = set(required_sources) | set(acceptable_sources)

        print("-" * 70)
        print(f"Test {index}/{len(TEST_CASES)}")
        print(f"Question: {question}")
        print(f"Required sources: {required_sources}")
        print(f"Acceptable sources: {acceptable_sources}")

        result = {
            "question": question,
            "required_sources": required_sources,
            "acceptable_sources": acceptable_sources,
            "actual_sources": [],
            "status": "ERROR",
            "error": None,
        }

        try:
            retriever = get_retriever(query=question)
            documents = retrieve_documents(retriever, question)

            actual_sources = sorted({
                source
                for document in documents
                if (source := get_source_name(document))
            })

            actual_set = set(actual_sources)
            required_set = set(required_sources)

            missing_required = sorted(required_set - actual_set)
            unexpected_sources = sorted(actual_set - allowed_sources)

            result["actual_sources"] = actual_sources
            result["retrieved_document_count"] = len(documents)
            result["missing_required_sources"] = missing_required
            result["unexpected_sources"] = unexpected_sources

            if required_sources:
                answerable_total += 1

                metrics = calculate_source_metrics(
                    required_sources,
                    actual_sources,
                )

                # PASS if all required sources were found and no
                # disallowed sources were retrieved.
                passed = (
                    not missing_required
                    and not unexpected_sources
                )

                answerable_passes += int(passed)
                answerable_metrics.append(metrics)

                result["metrics"] = metrics
                result["required_sources_found"] = not missing_required
                result["status"] = "PASS" if passed else "FAIL"

                print(f"Retrieved sources: {actual_sources}")
                print(f"Missing required sources: {missing_required}")
                print(f"Unexpected sources: {unexpected_sources}")
                print(
                    f"Precision: {metrics['precision']:.4f} | "
                    f"Recall: {metrics['recall']:.4f} | "
                    f"F1: {metrics['f1']:.4f}"
                )

            else:
                # An unanswerable query should retrieve no documents.
                abstention_correct = len(documents) == 0

                unanswerable_total += 1
                unanswerable_correct += int(abstention_correct)

                result["metrics"] = None
                result["abstention_correct"] = abstention_correct
                result["status"] = (
                    "PASS" if abstention_correct else "FAIL"
                )

                print(f"Retrieved sources: {actual_sources}")
                print(f"Retrieved document count: {len(documents)}")
                print(f"Correct abstention: {abstention_correct}")

            print(f"Result: {result['status']}")

        except Exception as exc:
            errors += 1
            result["error"] = str(exc)
            print(f"ERROR: {exc}")

        results.append(result)

    # ========================================================
    # SUMMARY
    # ========================================================

    completed_cases = sum(
        result["error"] is None
        for result in results
    )

    mean_precision = (
        sum(item["precision"] for item in answerable_metrics)
        / len(answerable_metrics)
        if answerable_metrics
        else None
    )

    mean_recall = (
        sum(item["recall"] for item in answerable_metrics)
        / len(answerable_metrics)
        if answerable_metrics
        else None
    )

    mean_f1 = (
        sum(item["f1"] for item in answerable_metrics)
        / len(answerable_metrics)
        if answerable_metrics
        else None
    )

    summary = {
        "mode": "retrieval_only",
        "llm_generation_enabled": False,
        "llm_judge_enabled": False,
        "total_cases": len(TEST_CASES),
        "completed_cases": completed_cases,
        "errors": errors,
        "answerable_cases": answerable_total,
        "answerable_strict_passes": answerable_passes,
        "answerable_pass_rate": (
            round(answerable_passes / answerable_total, 4)
            if answerable_total
            else None
        ),
        "unanswerable_cases": unanswerable_total,
        "correct_abstentions": unanswerable_correct,
        "abstention_accuracy": (
            round(unanswerable_correct / unanswerable_total, 4)
            if unanswerable_total
            else None
        ),
        "mean_source_precision": (
            round(mean_precision, 4)
            if mean_precision is not None
            else None
        ),
        "mean_source_recall": (
            round(mean_recall, 4)
            if mean_recall is not None
            else None
        ),
        "mean_source_f1": (
            round(mean_f1, 4)
            if mean_f1 is not None
            else None
        ),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }

    report = {
        "summary": summary,
        "results": results,
    }

    with REPORT_PATH.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)

    print()
    print("=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"Total tests: {summary['total_cases']}")
    print(f"Completed tests: {summary['completed_cases']}")
    print(f"Errors: {summary['errors']}")
    print(
        "Answerable strict pass rate: "
        f"{summary['answerable_strict_passes']}/"
        f"{summary['answerable_cases']}"
    )

    if summary["mean_source_precision"] is not None:
        print(f"Mean source precision: {summary['mean_source_precision']:.4f}")
        print(f"Mean source recall: {summary['mean_source_recall']:.4f}")
        print(f"Mean source F1: {summary['mean_source_f1']:.4f}")

    if summary["abstention_accuracy"] is not None:
        print(
            f"Correct abstentions: {summary['correct_abstentions']}/"
            f"{summary['unanswerable_cases']}"
        )
        print(f"Abstention accuracy: {summary['abstention_accuracy']:.4f}")

    print(f"\nReport saved to: {REPORT_PATH}")
    print("=" * 70)


if __name__ == "__main__":
    main()