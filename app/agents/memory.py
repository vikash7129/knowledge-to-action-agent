
from .state import AgentState


MAX_CONVERSATION_TURNS = 5


def update_memory(state: AgentState) -> dict:
    """
    Store recent conversation turns in the agent state.

    Keeps the latest five turns and safely handles
    missing or malformed history and response values.
    """

    history = state.get("conversation_history", [])

    if not isinstance(history, list):
        history = []

    user_input = state.get("user_input", "")
    final_response = state.get("final_response", "")
    route = state.get("route", "")

    # Normalize values to avoid storing unexpected data types.
    if not isinstance(user_input, str):
        user_input = str(user_input) if user_input is not None else ""

    if not isinstance(final_response, str):
        final_response = (
            str(final_response)
            if final_response is not None
            else ""
        )

    if not isinstance(route, str):
        route = str(route) if route is not None else ""

    new_conversation = {
        "user": user_input,
        "assistant": final_response,
        "route": route,
    }

    # Copy the list rather than modifying the original history.
    updated_history = list(history)
    updated_history.append(new_conversation)

    return {
        "conversation_history": updated_history[-MAX_CONVERSATION_TURNS:]
    }
