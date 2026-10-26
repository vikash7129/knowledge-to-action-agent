
from app.rag.retriever import get_retriever
from app.rag.rag_chain import generate_answer


def rag_agent(state):
    question = (
        state.get("contextualized_query")
        or state.get("user_input", "")
    )

    if not isinstance(question, str) or not question.strip():
        answer = "Please provide a question."
        return {
            "results": [],
            "final_response": answer,
        }

    retry_count = state.get("retry_count", 0)
    previous_critique = state.get("critique", "")

    retriever = get_retriever(query=question)
    documents = retriever.invoke(question)

    generation_question = question

    if retry_count > 0 and previous_critique.strip():
        generation_question = f"""
Original user question:
{question}

Previous critic feedback:
{previous_critique}

Instructions:
- Correct the specific issue identified by the critic.
- Answer the original question directly.
- Base document-related factual claims on retrieved evidence.
- If the evidence is insufficient, clearly say so.
- Do not invent facts or sources.
"""

    answer = generate_answer(
        question=generation_question,
        documents=documents,
        conversation_history=state.get("conversation_history", []),
    )

    # Pass actual retrieved evidence to the critic.
    evidence = []

    for document in documents:
        metadata = document.metadata or {}

        evidence.append({
            "content": document.page_content,
            "source": (
                metadata.get("source")
                or metadata.get("filename")
                or "Unknown source"
            ),
            "page": metadata.get("page"),
        })

    return {
        "results": evidence,
        "final_response": answer,
    }
