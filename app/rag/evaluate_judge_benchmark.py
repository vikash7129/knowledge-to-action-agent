
import json
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.documents import Document
from app.rag.answer_evaluation import evaluate_answer_with_llm


REPORT_DIR = Path("reports")
REPORT_PATH = REPORT_DIR / "llm_judge_benchmark.json"

DOCUMENTS = [
    Document(
        page_content=(
            "Reinforcement learning trains an agent through interaction "
            "with an environment. The agent receives rewards for good "
            "actions and penalties for bad actions. The goal is to "
            "maximize the total reward."
        ),
        metadata={"source": "ml_notes.txt"},
    )
]

QUESTION = "How does reinforcement learning work?"

CASES = [
    {
        "name": "Supported answer",
        "answer": (
            "An agent interacts with an environment and receives rewards "
            "for good actions and penalties for bad actions. It learns "
            "to maximize the total reward."
        ),
        "expected": "supported",
    },
    {
        "name": "Completely unsupported answer",
        "answer": (
            "Reinforcement learning requires quantum crystals and "
            "guarantees a perfect reward after exactly three actions."
        ),
        "expected": "unsupported",
    },
    {
        "name": "Partially unsupported answer",
        "answer": (
            "An agent learns through interaction with an environment "
            "and receives rewards and penalties. Every agent also "
            "becomes perfect after exactly three attempts."
        ),
        "expected": "partially_supported",
    },
    {
        "name": "Contradictory answer",
        "answer": (
            "Reinforcement learning agents never interact with an "
            "environment, receive no rewards, and do not learn from "
            "actions."
        ),
        "expected": "unsupported",
    },
]


def classify_score(score):
    if score is None:
        return "UNAVAILABLE"

    if score >= 0.75:
        return "HIGH"

    if score <= 0.40:
        return "LOW"

    return "MEDIUM"


def expected_band(expected):
    mapping = {
        "supported": "HIGH",
        "unsupported": "LOW",
        "partially_supported": "MEDIUM",
    }
    return mapping[expected]


def main():
    print("=" * 70)
    print("LLM JUDGE MULTI-CASE BENCHMARK")
    print("=" * 70)

    results = []

    for index, case in enumerate(CASES, start=1):
        print(f"\n[{index}/{len(CASES)}] {case['name']}")

        result = evaluate_answer_with_llm(
            question=QUESTION,
            answer=case["answer"],
            documents=DOCUMENTS,
        )

        judge_status = result.get("judge_status", "unknown")
        score = None
        reasons = result.get("judge_reasons", {})

        if judge_status == "success":
            score = result.get("judge_faithfulness")

            if score is not None:
                score = float(score)

        band = classify_score(score)

        passed = (
            score is not None
            and band == expected_band(case["expected"])
        )

        record = {
            "name": case["name"],
            "expected_category": case["expected"],
            "judge_status": judge_status,
            "faithfulness_score": score,
            "score_band": band,
            "expected_band": expected_band(case["expected"]),
            "passed": passed,
            "explanation": reasons.get("faithfulness"),
            "judge_error": result.get("judge_error"),
        }

        results.append(record)

        print("Expected category:", case["expected"])
        print("Judge status:", judge_status.upper())
        print("Faithfulness score:", score)
        print("Score band:", band)
        print("Case result:", "PASS" if passed else "FAIL")

        if record["explanation"]:
            print("Explanation:", record["explanation"])

        if record["judge_error"]:
            print("Error:", record["judge_error"])

    successful = [
        item for item in results
        if item["faithfulness_score"] is not None
        and item["judge_status"] == "success"
    ]

    passed_count = sum(item["passed"] for item in results)

    mean_score = (
        sum(item["faithfulness_score"] for item in successful)
        / len(successful)
        if successful
        else None
    )

    summary = {
        "total_cases": len(CASES),
        "successful_judge_calls": len(successful),
        "passed_cases": passed_count,
        "failed_cases": len(CASES) - passed_count,
        "case_classification_accuracy": (
            passed_count / len(CASES)
        ),
        "mean_faithfulness_score": mean_score,
        "overall_status": (
            "PASS"
            if len(successful) == len(CASES)
            and passed_count == len(CASES)
            else "REVIEW"
        ),
    }

    report = {
        "benchmark_name": "LLM Judge Multi-Case Benchmark",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "question": QUESTION,
        "summary": summary,
        "cases": results,
        "limitations": [
            "This benchmark contains only four test cases.",
            "Scores depend on the judge model and its evaluation behavior.",
            "Passing this benchmark does not establish production reliability.",
        ],
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    with REPORT_PATH.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=4, ensure_ascii=False)

    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)
    print(f"Successful judge calls: {len(successful)}/{len(CASES)}")
    print(f"Passed cases: {passed_count}/{len(CASES)}")
    print(f"Failed cases: {len(CASES) - passed_count}/{len(CASES)}")
    print(
        "Case classification accuracy: "
        f"{summary['case_classification_accuracy']:.2%}"
    )

    if mean_score is not None:
        print(f"Mean faithfulness score: {mean_score:.4f}")

    print("Overall status:", summary["overall_status"])
    print("Report saved to:", REPORT_PATH)


if __name__ == "__main__":
    main()
