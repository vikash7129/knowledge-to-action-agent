from app.rag.retriever import get_retriever


TEST_QUERIES = [
    "What is deep learning?",
    "Explain reinforcement learning using ml_notes.txt",
    "Compare machine learning, deep learning, and artificial intelligence",
    "What is machine learning?",
    "What is artificial intelligence?",
    "What is the difference between supervised and unsupervised learning?",
    "What are CNN and RNN used for?",
    "What does LSTM handle?",
    "Explain quantum computing.",
]


def get_source_name(document):
    metadata = getattr(document, "metadata", {}) or {}
    source = metadata.get("source") or metadata.get("filename")
    return str(source).replace("\\", "/").split("/")[-1] if source else "UNKNOWN"


def main():
    print("=" * 70)
    print("RETRIEVAL RELEVANCE SCORE DIAGNOSTICS")
    print("=" * 70)

    for query in TEST_QUERIES:
        print("\n" + "-" * 70)
        print(f"Query: {query}")
        print("-" * 70)

        try:
            retriever = get_retriever(query=query)

            if hasattr(retriever, "invoke"):
                documents = retriever.invoke(query)
            else:
                documents = retriever.get_relevant_documents(query)

            if not documents:
                print("No documents returned by the retriever.")
                continue

            for rank, document in enumerate(documents, start=1):
                metadata = getattr(document, "metadata", {}) or {}
                score = metadata.get("relevance_score")
                preview = " ".join(
                    (getattr(document, "page_content", "") or "").split()
                )[:240]

                print(f"\nRank: {rank}")
                print(f"Source: {get_source_name(document)}")
                print(f"FlashRank relevance score: {score}")
                print(f"Text preview: {preview}")

        except Exception as exc:
            print(f"ERROR: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 70)
    print("DIAGNOSTICS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()