from typing import TypedDict


class ConversationTurn(TypedDict):
    user: str
    assistant: str
    route: str


class ExecutionLog(TypedDict):
    tool: str
    input: str
    status: str
    result: str


class AgentState(TypedDict):
    user_input: str
    contextualized_query: str

    route: str

    plan: list[str]
    results: list[str]

    final_response: str
    critique: str

    retry_count: int

    conversation_history: list[ConversationTurn]

    execution_logs: list[ExecutionLog]