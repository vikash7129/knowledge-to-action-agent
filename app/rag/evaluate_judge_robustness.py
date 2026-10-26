
from langchain_core.documents import Document

from app.rag.answer_evaluation import evaluate_answer_with_llm


def print_result(title, result):
    print("\n" + "=" * 65)
    print(title)
    print("=" * 65)
    print("Judge status:", result["judge_status"].upper())

    if result["judge_status"] != "success":
        print("Reason:", result.get("judge_error"))
        return

    print(
        "Context relevance:",
        result["judge_context_relevance"],
    )
    print(
        "Answer relevance:",
        result["judge_answer_relevance"],
    )
    print(
        "Faithfulness:",
        result["judge_faithfulness"],
    )

    for metric, explanation in result.get("judge_reasons", {}).items():
        print(f"{metric}: {explanation}")


def main():
    question = "How does reinforcement learning work?"

    documents = [
        Document(
            page_content=(
                "Reinforcement learning trains an agent through "
                "interaction with an environment. The agent receives "
                "rewards for good actions and penalties for bad actions. "
                "The goal is to maximize the total reward."
            ),
            metadata={"source": "ml_notes.txt"},
        )
    ]

    supported_answer = (
        "Reinforcement learning trains an agent by interacting "
        "with an environment. It receives rewards for good actions "
        "and penalties for bad actions to maximize total reward."
    )

    unsupported_answer = (
        "Reinforcement learning requires quantum crystals to operate. "
        "Every agent is guaranteed to receive a perfect reward "
        "after exactly three actions."
    )

    print("=" * 65)
    print("LLM JUDGE ROBUSTNESS TEST")
    print("The unsupported answer below is intentionally fabricated.")
    print("=" * 65)

    supported_result = evaluate_answer_with_llm(
        question=question,
        answer=supported_answer,
        documents=documents,
    )

    print_result("TEST 1: SUPPORTED ANSWER", supported_result)

    unsupported_result = evaluate_answer_with_llm(
        question=question,
        answer=unsupported_answer,
        documents=documents,
    )

    print_result("TEST 2: UNSUPPORTED ANSWER", unsupported_result)

    empty_result = evaluate_answer_with_llm(
        question=question,
        answer="I cannot answer this question.",
        documents=[],
    )

    print_result("TEST 3: NO RETRIEVED DOCUMENTS", empty_result)

    print("\n" + "=" * 65)
    print("ROBUSTNESS SUMMARY")
    print("=" * 65)

    if (
        supported_result["judge_status"] == "success"
        and unsupported_result["judge_status"] == "success"
    ):
        supported_score = supported_result["judge_faithfulness"]
        unsupported_score = unsupported_result["judge_faithfulness"]

        print(f"Supported answer faithfulness: {supported_score:.4f}")
        print(f"Unsupported answer faithfulness: {unsupported_score:.4f}")

        if supported_score > unsupported_score:
            print("Result: PASS — judge distinguishes the two answers.")
        else:
            print(
                "Result: REVIEW — judge did not clearly distinguish "
                "the two answers in this run."
            )
    else:
        print("Result: INCONCLUSIVE — one or both judge calls failed.")

    print(
        "No-document handling:",
        "PASS" if empty_result["judge_status"] == "skipped" else "REVIEW",
    )

    print(
        "\nReminder: A single LLM judge run is not proof of "
        "reliable hallucination detection."
    )


if __name__ == "__main__":
    main()
