from dotenv import load_dotenv

load_dotenv()

from app.rag.retriever import get_retriever


retriever = get_retriever()

questions = [
    "What is Reinforcement Learning?",
    "What is Deep Learning?",
    "What is the difference between Machine Learning and Deep Learning?"
]


for question in questions:

    print("\n==============================")
    print("QUESTION:", question)
    print("==============================")

    documents = retriever.invoke(question)

    print("Documents found:", len(documents))

    for i, doc in enumerate(documents, start=1):

        print(f"\n--- DOCUMENT {i} ---")

        print("SOURCE:")
        print(doc.metadata.get("source"))

        print("\nCONTENT:")
        print(doc.page_content[:300])