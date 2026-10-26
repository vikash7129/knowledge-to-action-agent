from dotenv import load_dotenv

load_dotenv()

from app.rag.retriever import get_retriever


# Get retriever from existing ChromaDB
retriever = get_retriever()


# Test question
question = "according to ai_notes.txt, what is deep learning?"


# Search relevant documents
documents = retriever.invoke(question)


print("\n===== RETRIEVER TEST =====")
print("Question:", question)
print("Documents found:", len(documents))


for i, doc in enumerate(documents, start=1):

    print(f"\n===== DOCUMENT {i} =====")

    print(doc.page_content)

    print("\nMetadata:")
    print(doc.metadata)