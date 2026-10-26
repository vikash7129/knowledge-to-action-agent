from .state import AgentState


MAX_RETRIES = 2


def get_retry_count(state: AgentState) -> int:
    return int(state.get("retry_count", 0))


def can_retry(state: AgentState) -> bool:
    return get_retry_count(state) < MAX_RETRIES


def should_retry(state: AgentState) -> str:
    """
    Decide whether the workflow should retry the executor
    or finish with a fallback response.
    """

    retry_count = get_retry_count(state)

    critique = state.get(
        "critique",
        ""
    )

    # No error → continue normally
    if not critique:
        return "success"

    # Retry if attempts remain
    if retry_count < MAX_RETRIES:
        return "retry"

    # Retry limit reached
    return "fallback"


def create_recovery_response(
    state: AgentState,
    error_message: str,
):
    retry_count = get_retry_count(state)

    if retry_count >= MAX_RETRIES:

        message = (
            "The agent could not complete the request "
            "after multiple attempts. "
            "Please try again with a simpler request."
        )

        return {
            "results": [message],
            "final_response": message,
            "critique": (
                f"Recovery failed after "
                f"{retry_count} retries. "
                f"Error: {error_message}"
            ),
            "retry_count": retry_count,
        }

    new_retry_count = retry_count + 1

    message = (
        "The agent encountered a temporary error. "
        "The request will be retried safely."
    )

    return {
        "results": [message],
        "final_response": message,
        "critique": (
            f"Temporary agent error: "
            f"{error_message}"
        ),
        "retry_count": new_retry_count,
    }


def create_fallback_response(
    error_message: str
):
    message = (
        "I could not complete the request because "
        "an internal error occurred. "
        "Please try again."
    )

    return {
        "results": [message],
        "final_response": message,
        "critique": (
            f"Fallback activated: "
            f"{error_message}"
        ),
    }