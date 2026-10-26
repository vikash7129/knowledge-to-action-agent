
import json
from datetime import datetime, timezone
from pathlib import Path

from app.rag.retriever import get_retriever
from app.rag.rag_chain import generate_answer
from app.rag.answer_evaluation import (
    evaluate_answer,
    evaluate_answer_with_llm,
)


REPORT_DIR = Path("reports")
REPORT_PATH = REPORT_DIR / "real_rag_evaluation.json"


# expected_sources contains all sources considered relevant
# for answering each question, not necessarily every stored source.
EVALUATION_DATASET = [
    {
        "question": "Explain reinforcement learning using ml_notes.txt",
        "expected_sources": ["ml_notes.txt"],
        "expected_answerable": True,
    },
    {
        "question": "What is deep learning?",
        "expected_sources": ["dl_notes.txt", "ai_notes.txt"],
        "expected_answerable": True,
    },
    {
        "question": (
            "Compare machine learning, deep learning, "
            "and artificial intelligence"
        ),
        "expected_sources": [
            "ai_notes.txt",
            "dl_notes.txt",
            "ml_notes.txt",
        ],
        "expected_answerable": True,
    },
    {
        "question": "What is machine learning?",
        "expected_sources": ["ai_notes.txt", "ml_notes.txt"],
        "expected_answerable": True,
    },
    {
        "question": (
            "What is the difference between supervised "
            "and unsupervised learning?"
        ),
        "expected_sources": ["ml_notes.txt"],
        "expected_answerable": True,
    },
    {
        "question": "What are CNN and RNN used for?",
        "expected_sources": ["dl_notes.txt"],
        "expected_answerable": True,
    },
    {
        "question": "What does LSTM handle?",
        "expected_sources": ["dl_notes.txt"],
        "expected_answerable": True,
    },
    {
        "question": "What is artificial intelligence?",
        "expected_sources": ["ai_notes.txt"],
        "expected_answerable": True,
    },
    {
        "question": "Explain quantum computing.",
        "expected_sources": [],
        "expected_answerable": False,
    },
    {
        "question": "Explain photosynthesis in plants.",
        "expected_sources": [],
        "expected_answerable": False,
    },
    {
        "question": "Who won the 2022 FIFA World Cup?",
        "expected_sources": [],
        "expected_answerable": False,
    },
    {
        "question": "What is the capital of Japan?",
        "expected_sources": [],
        "expected_answerable": False,
    },
]


def extract_answer_text(answer):
    if not isinstance(answer, str):
        answer = str(answer)

    return answer.split("\n\nSources:", maxsplit=1)[0].strip()


def print_score(label, score):
    if isinstance(score, (int, float)) and not isinstance(score, bool):
        print(f"{label}: {score:.4f}")
    else:
        print(f"{label}: N/A")


def safe_score(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)

    return None


def calculate_source_metrics(expected_sources, actual_sources):
    expected = set(expected_sources)
    actual = set(actual_sources)

    # For an unanswerable question, retrieving no sources is ideal.
    if not expected:
        if not actual:
            return {
                "precision": 1.0,
                "recall": 1.0,
                "f1": 1.0,
            }

        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
        }

    if not actual:
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
        }

    true_positive = len(expected & actual)

    precision = true_positive / len(actual)
    recall = true_positive / len(expected)

    if precision + recall:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def evaluate_case(case, index):
    question = case["question"]
    expected_sources = set(case["expected_sources"])
    expected_answerable = case["expected_answerable"]

    record = {
        "case_number": index,
        "question": question,
        "expected_sources": sorted(expected_sources),
        "expected_answerable": expected_answerable,
        "retrieved_sources": [],
        "retrieved_chunks": 0,
        "missing_expected_sources": [],
        "unexpected_sources": [],
        "source_pass": False,
        "source_metrics": None,
        "answer": None,
        "lexical_evaluation": None,
        "judge_evaluation": None,
        "status": "started",
        "error": None,
    }

    print("\n" + "=" * 70)
    print(f"TEST CASE {index}/{len(EVALUATION_DATASET)}")
    print("Question:", question)
    print(
        "Expected answerability:",
        "ANSWERABLE" if expected_answerable else "NOT IN EXPECTED DOCUMENTS",
    )
    print("-" * 70)

    try:
        # 1. Retrieve documents using the real hybrid retriever.
        retriever = get_retriever(query=question)
        documents = retriever.invoke(question)

        record["retrieved_chunks"] = len(documents)

        actual_sources = {
            (document.metadata or {}).get("source")
            for document in documents
            if (document.metadata or {}).get("source")
        }

        record["retrieved_sources"] = sorted(actual_sources)

        missing_sources = expected_sources - actual_sources
        unexpected_sources = actual_sources - expected_sources

        record["missing_expected_sources"] = sorted(missing_sources)
        record["unexpected_sources"] = sorted(unexpected_sources)

        source_metrics = calculate_source_metrics(
            expected_sources,
            actual_sources,
        )
        record["source_metrics"] = source_metrics

        # For answerable questions, all expected sources must be found.
        # For unanswerable questions, retrieval should return no sources.
        if expected_answerable:
            source_pass = not missing_sources
        else:
            source_pass = len(actual_sources) == 0

        record["source_pass"] = source_pass

        print("Retrieved sources:", sorted(actual_sources))
        print("Retrieved chunks:", len(documents))
        print("Expected sources:", sorted(expected_sources))
        print("Missing expected sources:", sorted(missing_sources))
        print("Unexpected sources:", sorted(unexpected_sources))
        print("Retrieval test:", "PASS" if source_pass else "FAIL")

        print_score("Source precision", source_metrics["precision"])
        print_score("Source recall", source_metrics["recall"])
        print_score("Source F1", source_metrics["f1"])

        # 2. Generate an answer even when retrieval returns no documents.
        # This lets us inspect the system's missing-evidence behavior.
        answer = generate_answer(
            question=question,
            documents=documents,
            conversation_history=None,
        )

        answer_text = extract_answer_text(answer)
        record["answer"] = answer_text

        print("\nGenerated answer:")
        print(answer_text or "(Empty answer)")

        # 3. Evaluate lexical indicators.
        lexical = evaluate_answer(
            question=question,
            answer=answer_text,
            documents=documents,
        )

        lexical_record = {
            "context_relevance": safe_score(
                lexical.get("context_relevance")
            ),
            "answer_relevance": safe_score(
                lexical.get("answer_relevance")
            ),
            "faithfulness_indicator": safe_score(
                lexical.get("faithfulness_indicator")
            ),
            "warnings": lexical.get("warnings", []),
        }

        record["lexical_evaluation"] = lexical_record

        print("\n--- Lexical evaluation ---")
        print_score(
            "Context relevance",
            lexical_record["context_relevance"],
        )
        print_score(
            "Answer relevance",
            lexical_record["answer_relevance"],
        )
        print_score(
            "Faithfulness indicator",
            lexical_record["faithfulness_indicator"],
        )

        if lexical_record["warnings"]:
            print("Warnings:")
            for warning in lexical_record["warnings"]:
                print("-", warning)

        # 4. Evaluate grounding with the LLM Judge.
        print("\n--- LLM-as-a-Judge evaluation ---")

        judge = evaluate_answer_with_llm(
            question=question,
            answer=answer_text,
            documents=documents,
        )

        judge_record = {
            "status": judge.get("judge_status", "unknown"),
            "context_relevance": safe_score(
                judge.get("judge_context_relevance")
            ),
            "answer_relevance": safe_score(
                judge.get("judge_answer_relevance")
            ),
            "faithfulness": safe_score(
                judge.get("judge_faithfulness")
            ),
            "reasons": judge.get("judge_reasons", {}),
            "error": judge.get("judge_error"),
        }

        record["judge_evaluation"] = judge_record

        print("Judge status:", judge_record["status"].upper())

        if judge_record["status"] == "success":
            print_score(
                "Judge context relevance",
                judge_record["context_relevance"],
            )
            print_score(
                "Judge answer relevance",
                judge_record["answer_relevance"],
            )
            print_score(
                "Judge faithfulness",
                judge_record["faithfulness"],
            )

            for metric_name, reason in judge_record["reasons"].items():
                if reason:
                    print(f"{metric_name} explanation: {reason}")

        elif judge_record["error"]:
            print("Judge message:", judge_record["error"])

        record["status"] = "completed"

        print(
            "\nNote: Judge scores are evaluation indicators, "
            "not guarantees of factual correctness."
        )

        return record

    except Exception as error:
        record["status"] = "error"
        record["error"] = f"{type(error).__name__}: {error}"

        print("TEST CASE ERROR:", record["error"])
        return record


def mean_metric(results, metric_name):
    values = [
        item["source_metrics"][metric_name]
        for item in results
        if item.get("source_metrics") is not None
    ]

    if not values:
        return None

    return sum(values) / len(values)


def build_summary(results):
    total = len(results)

    source_passed = sum(
        item["source_pass"] for item in results
    )

    judge_succeeded = sum(
        (item.get("judge_evaluation") or {}).get("status") == "success"
        for item in results
    )

    judge_errors = sum(
        (item.get("judge_evaluation") or {}).get("status") == "error"
        for item in results
    )

    judge_skipped = sum(
        (item.get("judge_evaluation") or {}).get("status") == "skipped"
        for item in results
    )

    pipeline_errors = sum(
        item["status"] == "error" for item in results
    )

    faithfulness_scores = [
        item["judge_evaluation"]["faithfulness"]
        for item in results
        if item.get("judge_evaluation")
        and item["judge_evaluation"].get("status") == "success"
        and item["judge_evaluation"].get("faithfulness") is not None
    ]

    mean_faithfulness = (
        sum(faithfulness_scores) / len(faithfulness_scores)
        if faithfulness_scores
        else None
    )

    answerable_cases = [
        item for item in results
        if item["expected_answerable"]
    ]

    unanswerable_cases = [
        item for item in results
        if not item["expected_answerable"]
    ]

    return {
        "total_cases": total,
        "answerable_cases": len(answerable_cases),
        "unanswerable_cases": len(unanswerable_cases),
        "retrieval_tests_passed": source_passed,
        "retrieval_test_pass_rate": (
            source_passed / total if total else 0.0
        ),
        "source_coverage_passed": source_passed,
        "source_coverage_rate": (
            source_passed / total if total else 0.0
        ),
        "mean_source_precision": mean_metric(results, "precision"),
        "mean_source_recall": mean_metric(results, "recall"),
        "mean_source_f1": mean_metric(results, "f1"),
        "judge_successful": judge_succeeded,
        "judge_success_rate": judge_succeeded / total if total else 0.0,
        "judge_errors": judge_errors,
        "judge_skipped": judge_skipped,
        "pipeline_errors": pipeline_errors,
        "mean_judge_faithfulness": mean_faithfulness,
        "completed_cases": sum(
            item["status"] == "completed" for item in results
        ),
    }


def main():
    print("=" * 70)
    print("EXPANDED REAL RAG EVALUATION")
    print("Hybrid retrieval + lexical evaluation + LLM Judge")
    print("Total test cases:", len(EVALUATION_DATASET))
    print("=" * 70)

    results = []

    for index, case in enumerate(EVALUATION_DATASET, start=1):
        results.append(evaluate_case(case, index))

    summary = build_summary(results)

    report = {
        "benchmark_name": "Expanded Real RAG Answer Evaluation",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_size": len(EVALUATION_DATASET),
        "summary": summary,
        "results": results,
        "limitations": [
            "This is a small manually labelled evaluation dataset.",
            "Expected sources are human-defined relevance labels.",
            "Source metrics measure source-level overlap, not chunk-level relevance.",
            "Unanswerable tests expect no relevant documents in the current corpus.",
            "A retrieval pass does not guarantee that the generated answer is correct.",
            "Lexical metrics are heuristic indicators.",
            "LLM judge scores can be mistaken or inconsistent.",
            "A successful judge call does not prove that the judge's score is correct.",
            "The benchmark does not establish production reliability.",
        ],
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    with REPORT_PATH.open("w", encoding="utf-8") as file:
        json.dump(
            report,
            file,
            indent=4,
            ensure_ascii=False,
            allow_nan=False,
        )

    print("\n" + "=" * 70)
    print("FINAL EVALUATION SUMMARY")
    print("=" * 70)
    print("Total test cases:", summary["total_cases"])
    print("Answerable cases:", summary["answerable_cases"])
    print("Unanswerable cases:", summary["unanswerable_cases"])
    print(
        f"Retrieval tests passed: {summary['retrieval_tests_passed']}/"
        f"{summary['total_cases']}"
    )
    print(
        f"Retrieval test pass rate: "
        f"{summary['retrieval_test_pass_rate']:.2%}"
    )

    for metric in (
        "mean_source_precision",
        "mean_source_recall",
        "mean_source_f1",
        "mean_judge_faithfulness",
    ):
        print_score(metric.replace("_", " ").title(), summary[metric])

    print(
        f"Judge success rate: {summary['judge_success_rate']:.2%}"
    )
    print("Judge errors:", summary["judge_errors"])
    print("Pipeline errors:", summary["pipeline_errors"])
    print("Completed cases:", summary["completed_cases"])
    print("Report saved to:", REPORT_PATH)
    print("=" * 70)


if __name__ == "__main__":
    main()
