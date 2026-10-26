from langchain_google_genai import ChatGoogleGenerativeAI


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0
)


def resolve_context(
    question: str,
    conversation_history: list[str]
) -> str:

    # No previous conversation
    if not conversation_history:

        return question

    history_text = "\n".join(
        conversation_history[-6:]
    )

    prompt = f"""
You are a conversation context resolver.

Your ONLY job is to convert the current user
question into a standalone question.

Use ONLY the previous conversation to resolve
ambiguous references.

Previous conversation:
{history_text}

Current user question:
{question}

Rules:

1. If the current question is already clear,
   return it unchanged.

2. If the question contains words such as:
   "it", "its", "this", "that", "they",
   "them", "the above", or similar references,
   resolve them using the previous conversation.

3. NEVER guess the meaning from general knowledge.

4. Prefer the most recent relevant topic from
   the conversation.

5. Return ONLY the standalone question.

6. Do not provide an answer.

Example:

Previous conversation:
User: What is Reinforcement Learning?
Assistant: Reinforcement Learning is a type of
machine learning...

Current question:
Give me a simple example of it.

Output:
Give me a simple example of Reinforcement Learning.

Now resolve the current question.

Current question:
{question}
"""

    response = llm.invoke(prompt)

    resolved_question = str(
        response.content
    ).strip()

    return resolved_question