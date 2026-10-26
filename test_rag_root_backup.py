from dotenv import load_dotenv

load_dotenv()

from app.rag.loader import load_document
from app.rag.splitter import split_documents
from app.rag.retriever import get_retriever
from app.rag.rag_chain import generate_answer


# Load document
documents = load_document("data/test.txt")


# Create chunks
chunks = split_documents(documents)


# Create retriever
retriever = get_retriever(chunks)


# User question
query = "What is Machine Learning?"


# Retrieve relevant documents
results = retriever.invoke(query)


print("===== RETRIEVED INFORMATION =====")

for i, document in enumerate(results, start=1):

    print(f"\n--- Result {i} ---")
    print(document.page_content)


# Generate answer using Gemini
answer = generate_answer(
    query,
    results
)


print("\n===== FINAL RAG ANSWER =====")
print(answer)