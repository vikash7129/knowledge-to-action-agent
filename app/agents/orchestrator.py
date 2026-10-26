import re

from langchain_google_genai import (
    ChatGoogleGenerativeAI
)

from .state import AgentState


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0
)


def format_conversation_history(
    conversation_history
):

    history_text = ""

    for turn in conversation_history:

        # =========================
        # OLD MEMORY FORMAT
        # =========================

        if isinstance(turn, str):

            history_text += (
                turn
                + "\n\n"
            )

        # =========================
        # NEW MEMORY FORMAT
        # =========================

        elif isinstance(turn, dict):

            history_text += (
                f"User: "
                f"{turn.get('user', '')}\n"
                f"Assistant: "
                f"{turn.get('assistant', '')}\n"
                f"Previous Route: "
                f"{turn.get('route', '')}\n\n"
            )

    return history_text


def orchestrator_agent(
    state: AgentState
):

    # =========================
    # USER INPUT
    # =========================

    user_input = state["user_input"]

    # =========================
    # CONVERSATION HISTORY
    # =========================

    conversation_history = state.get(
        "conversation_history",
        []
    )

    recent_history = (
        conversation_history[-3:]
    )

    # =========================
    # FORMAT HISTORY
    # =========================

    history_text = (
        format_conversation_history(
            recent_history
        )
    )

    # =========================
    # DEFAULT QUERY
    # =========================

    contextualized_query = user_input

    # =========================
    # LOWERCASE QUERY
    # =========================

    user_input_lower = (
        user_input
        .lower()
        .strip()
    )

    # =========================
    # FOLLOW-UP DETECTION
    # =========================

    follow_up_patterns = [

        r"\bit\b",
        r"\bthis\b",
        r"\bthat\b",
        r"\bthese\b",
        r"\bthose\b",

        r"\bmore about\b",
        r"\btell me more\b",
        r"\bexplain it\b",
        r"\bhow does it\b",
        r"\bhow is it\b",

        r"\bgive me an example of it\b",
        r"\bgive me a simple example of it\b",

        r"\bwhat about this\b",
        r"\bwhat about that\b"
    ]

    is_follow_up = any(
        re.search(
            pattern,
            user_input_lower
        )
        for pattern in follow_up_patterns
    )

    # =========================
    # CONTEXTUALIZE FOLLOW-UP
    # =========================

    if (
        is_follow_up
        and conversation_history
    ):

        contextualize_prompt = f"""
You are a query contextualization assistant.

Recent conversation:

{history_text}

Current user question:

{user_input}

Rewrite the current question so that
it is completely understandable without
the previous conversation.

Rules:

1. Keep the original meaning.
2. Use the previous conversation only
   when necessary.
3. Identify what "it", "this", "that",
   or similar words refer to.
4. Do not add new information.
5. Return ONLY the rewritten question.

Rewritten question:
"""

        response = llm.invoke(
            contextualize_prompt
        )

        contextualized_query = str(
            response.content
        ).strip()

    # =========================
    # DEBUG
    # =========================

    print(
        "\n===== ORCHESTRATOR DEBUG ====="
    )

    print(
        "Original Query:",
        user_input
    )

    print(
        "Contextualized Query:",
        contextualized_query
    )

    # =========================
    # ROUTING
    # =========================

    routing_prompt = f"""
You are an AI Orchestrator.

Choose exactly ONE route.

rag:
Use for questions about Machine Learning,
Deep Learning, Reinforcement Learning,
AI concepts, or information that should
be answered from the local knowledge base.

planner:
Use for plans, roadmaps, strategies,
or multi-step project planning.

researcher:
Use ONLY for latest information,
current events, or web research.

executor:
Use for direct simple tasks.

Recent conversation:

{history_text}

Current user question:

{contextualized_query}

Important:

If the current question is a follow-up,
use the recent conversation to understand
its meaning.

Return ONLY one word:

rag
planner
researcher
executor
"""

    response = llm.invoke(
        routing_prompt
    )

    route = str(
        response.content
    ).strip().lower()

    # =========================
    # VALIDATION
    # =========================

    valid_routes = [
        "rag",
        "planner",
        "researcher",
        "executor"
    ]

    if route not in valid_routes:
        route = "rag"

    # =========================
    # RETURN
    # =========================

    return {
        "route": route,
        "contextualized_query":
            contextualized_query
    }