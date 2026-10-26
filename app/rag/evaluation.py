
from app.rag.retriever import get_retriever


TOP_K = 3

EVALUATION_DATASET = [
    {
        "query": "Explain reinforcement learning using ml_notes.txt",
        "relevant_sources": {"ml_notes.txt"},
    },
    {
        "query": "What is deep learning?",
        "relevant_sources": {"dl_notes.txt"},
    },
    {
        "query": (
            "Compare machine learning, deep learning, "
            "and artificial intelligence"
        ),
        "relevant_sources": {
            "ai_notes.txt",
            "dl_notes.txt",
            "ml_notes.txt",
        },
    },
]


def precision_at_k(retrieved_sources, relevant_sources, k=TOP_K):
    """Calculate Precision@K. Missing result positions count as irrelevant."""
    if k <= 0:
        raise ValueError("k must be greater than zero")

    relevant_count = sum(
        1
        for source in retrieved_sources[:k]
        if source and source in relevant_sources
    )

    return relevant_count / k


def recall_at_k(retrieved_sources, relevant_sources, k=TOP_K):
    """Calculate the fraction of relevant sources retrieved in the top K."""
    if k <= 0:
        raise ValueError("k must be greater than zero")

    if not relevant_sources:
        return 0.0

    found_sources = {
        source
        for source in retrieved_sources[:k]
        if source and source in relevant_sources
    }

    return len(found_sources) / len(relevant_sources)


def reciprocal_rank(retrieved_sources, relevant_sources):
    """Calculate the reciprocal rank of the first relevant result."""
    for rank, source in enumerate(retrieved_sources, start=1):
        if source and source in relevant_sources:
            return 1.0 / rank

    return 0.0


def evaluate_query(query, relevant_sources, k=TOP_K):
    """Run retrieval and report metrics, validation, and test status."""
    retriever = get_retriever(query=query)
    documents = retriever.invoke(query)

    retrieved_sources = [
        document.metadata.get("source")
        for document in documents
    ]

    missing_metadata_count = sum(
        1 for source in retrieved_sources if not source
    )

    valid_sources = [
        source for source in retrieved_sources if source
    ]

    found_sources = set(valid_sources) & set(relevant_sources)
    missing_relevant_sources = sorted(
        set(relevant_sources) - found_sources
    )

    errors = []

    if not documents:
        errors.append("No documents retrieved")

    if missing_metadata_count:
        errors.append(
            f"{missing_metadata_count} result(s) missing source metadata"
        )

    if missing_relevant_sources:
        errors.append(
            "Expected sources not retrieved: "
            + ", ".join(missing_relevant_sources)
        )

    return {
        "query": query,
        "expected_sources": sorted(relevant_sources),
        "retrieved_sources": retrieved_sources,
        "precision_at_k": precision_at_k(
            retrieved_sources, relevant_sources, k
        ),
        "recall_at_k": recall_at_k(
            retrieved_sources, relevant_sources, k
        ),
        "reciprocal_rank": reciprocal_rank(
            retrieved_sources, relevant_sources
        ),
        "missing_metadata_count": missing_metadata_count,
        "errors": errors,
        "passed": not errors,
    }


def run_evaluation():
    """Run all cases and average metrics over successful evaluations only."""
    print("=" * 65)
    print("RETRIEVAL QUALITY EVALUATION - STAGE 20.4")
    print("=" * 65)

    successful_results = []
    failed_count = 0

    for index, test_case in enumerate(EVALUATION_DATASET, start=1):
        query = test_case["query"]
        relevant_sources = test_case["relevant_sources"]

        print(f"\nTest {index}: {query}")

        try:
            result = evaluate_query(query, relevant_sources)

            print("Expected sources:", result["expected_sources"])
            print("Retrieved sources:", result["retrieved_sources"])
            print(
                f"Precision@{TOP_K}: "
                f"{result['precision_at_k']:.2f}"
            )
            print(
                f"Recall@{TOP_K}: "
                f"{result['recall_at_k']:.2f}"
            )
            print(
                f"Reciprocal Rank: "
                f"{result['reciprocal_rank']:.2f}"
            )
            print(
                "Missing source metadata:",
                result["missing_metadata_count"],
            )

            if result["passed"]:
                print("Status: PASS")
                successful_results.append(result)
            else:
                print("Status: FAIL")
                for error in result["errors"]:
                    print("  Issue:", error)
                failed_count += 1

        except Exception as error:
            print("Status: ERROR")
            print(f"  Issue: {type(error).__name__}: {error}")
            failed_count += 1

    total = len(EVALUATION_DATASET)
    passed_count = len(successful_results)

    print("\n" + "=" * 65)
    print("FINAL EVALUATION SUMMARY")
    print("=" * 65)
    print(f"Total test cases: {total}")
    print(f"Passed: {passed_count}")
    print(f"Failed or errored: {failed_count}")
    print(f"Evaluation coverage: {passed_count / total:.2%}" if total else
          "Evaluation coverage: N/A")

    if successful_results:
        count = len(successful_results)

        mean_precision = sum(
            item["precision_at_k"] for item in successful_results
        ) / count

        mean_recall = sum(
            item["recall_at_k"] for item in successful_results
        ) / count

        mrr = sum(
            item["reciprocal_rank"] for item in successful_results
        ) / count

        print("\nMetrics for passing cases only:")
        print(f"Mean Precision@{TOP_K}: {mean_precision:.2f}")
        print(f"Mean Recall@{TOP_K}: {mean_recall:.2f}")
        print(f"MRR: {mrr:.2f}")
    else:
        print("\nNo passing cases; aggregate metrics are unavailable.")

    if failed_count:
        print(
            "\nWARNING: Some cases failed. "
            "Metrics above do not include failed cases."
        )


if __name__ == "__main__":
    run_evaluation()
