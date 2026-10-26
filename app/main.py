
import os
import re
import sys
import sqlite3
import uuid

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

from app.agents.state import AgentState
from app.agents.orchestrator import orchestrator_agent
from app.agents.planner import planner_agent
from app.agents.executor import executor_agent
from app.agents.researcher import researcher_agent
from app.agents.critic import critic_agent
from app.agents.rag_agent import rag_agent
from app.agents.memory import update_memory
from app.agents.tracing import trace_agent


# ============================================================
# CONFIGURATION
# ============================================================

MEMORY_DB_PATH = "memory.db"
MAX_RETRIES = 2


# ============================================================
# SESSION FACT MEMORY
# ============================================================

def get_session_id():
    return os.getenv("AGENT_THREAD_ID", "user-1")


def init_session_fact_memory():
    with sqlite3.connect(MEMORY_DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS session_facts (
                session_id TEXT NOT NULL,
                fact_key TEXT NOT NULL,
                fact_value TEXT NOT NULL,
                PRIMARY KEY (session_id, fact_key)
            )
        """)


def save_session_fact(key, value):
    with sqlite3.connect(MEMORY_DB_PATH) as conn:
        conn.execute("""
            INSERT INTO session_facts
                (session_id, fact_key, fact_value)
            VALUES (?, ?, ?)
            ON CONFLICT(session_id, fact_key)
            DO UPDATE SET fact_value = excluded.fact_value
        """, (get_session_id(), key, value))


def get_session_fact(key):
    with sqlite3.connect(MEMORY_DB_PATH) as conn:
        row = conn.execute("""
            SELECT fact_value
            FROM session_facts
            WHERE session_id = ? AND fact_key = ?
        """, (get_session_id(), key)).fetchone()

    return row[0] if row else None


def handle_simple_project_memory(user_input):
    text = user_input.strip()

    match = re.search(
        r"\b(?:my|our)\s+project\s+name\s+is\s+"
        r"([^.!?\n]+)",
        text,
        re.IGNORECASE,
    )

    if match:
        project_name = match.group(1).strip().rstrip(" ,")

        if project_name and len(project_name) <= 80:
            save_session_fact("project_name", project_name)
            return (
                f"Saved for this session. "
                f"Your project name is {project_name}."
            )

    is_project_name_question = bool(re.search(
        r"\b(?:what(?:'s|\s+is)|tell\s+me)\b.*"
        r"\b(?:my|our)\s+project\s+name\b"
        r"|\b(?:my|our)\s+project\s+name\b.*"
        r"\b(?:what|again)\b",
        text,
        re.IGNORECASE,
    ))

    if is_project_name_question:
        project_name = get_session_fact("project_name")

        if project_name:
            return f"Your project name is {project_name}."

        return "I don't have a project name saved in this session yet."

    return None


# ============================================================
# BUILD WORKFLOW
# ============================================================

workflow = StateGraph(AgentState)

workflow.add_node(
    "orchestrator",
    trace_agent("orchestrator", orchestrator_agent),
)
workflow.add_node(
    "planner",
    trace_agent("planner", planner_agent),
)
workflow.add_node(
    "researcher",
    trace_agent("researcher", researcher_agent),
)
workflow.add_node(
    "executor",
    trace_agent("executor", executor_agent),
)
workflow.add_node(
    "rag",
    trace_agent("rag", rag_agent),
)
workflow.add_node(
    "critic",
    trace_agent("critic", critic_agent),
)
workflow.add_node(
    "memory",
    trace_agent("memory", update_memory),
)

workflow.add_edge(START, "orchestrator")


# ============================================================
# ORCHESTRATOR ROUTING
# ============================================================

def route_request(state: AgentState):
    route = state.get("route", "executor")

    if route not in {"planner", "researcher", "executor", "rag"}:
        return "executor"

    return route


workflow.add_conditional_edges(
    "orchestrator",
    route_request,
    {
        "planner": "planner",
        "researcher": "researcher",
        "executor": "executor",
        "rag": "rag",
    },
)


# ============================================================
# AGENTS TO CRITIC
# ============================================================

workflow.add_edge("planner", "critic")
workflow.add_edge("researcher", "critic")
workflow.add_edge("executor", "critic")
workflow.add_edge("rag", "critic")


# ============================================================
# CRITIC ROUTER — HONEST VERIFICATION AND RETRIES
# ============================================================

def critic_router(state: AgentState):
    critique = str(state.get("critique", "")).strip().upper()
    retry_count = state.get("retry_count", 0)
    route = state.get("route", "executor")

    print("\n===== CRITIC ROUTER =====")
    print("Route:", route)
    print("Retry count:", retry_count)
    print("Maximum retries:", MAX_RETRIES)

    if re.search(r"\bSTATUS\s*:\s*PASS\b", critique):
        print("Verification: PASS")
        return "pass"

    if retry_count >= MAX_RETRIES:
        print("Verification: RETRY LIMIT REACHED")
        return "failed"

    print("Verification: RETRY")

    if route == "rag":
        return "retry_rag"

    if route == "planner":
        return "retry_planner"

    if route == "researcher":
        return "retry_researcher"

    return "retry_executor"


workflow.add_conditional_edges(
    "critic",
    critic_router,
    {
        "pass": "memory",
        "failed": "memory",
        "retry_rag": "rag",
        "retry_planner": "planner",
        "retry_researcher": "researcher",
        "retry_executor": "executor",
    },
)

workflow.add_edge("memory", END)


# ============================================================
# MAIN APPLICATION
# IMPORTANT: Interactive code runs only when main() is called.
# ============================================================

def main():
    # USER INPUT
    user_input = input("What do you want to accomplish?\n> ").strip()

    init_session_fact_memory()

    direct_answer = handle_simple_project_memory(user_input)

    if direct_answer is not None:
        print("\n===== SESSION MEMORY =====")
        print("STATUS: PASS")
        print(direct_answer)
        return

    # INITIAL STATE
    initial_state = {
        "user_input": user_input,
        "contextualized_query": "",
        "route": "",
        "plan": [],
        "results": [],
        "final_response": "",
        "critique": "",
        "retry_count": 0,
        "conversation_history": [],
        "execution_logs": [],
    }

    # CHECKPOINT CONFIG
    config = {
        "configurable": {
            "thread_id": get_session_id(),
        }
    }

    # RUN WORKFLOW
    os.environ["AGENT_TRACE_RUN_ID"] = uuid.uuid4().hex

    with SqliteSaver.from_conn_string(MEMORY_DB_PATH) as checkpointer:
        app = workflow.compile(checkpointer=checkpointer)

        previous_state = app.get_state(config)

        if previous_state and previous_state.values:
            previous_history = previous_state.values.get(
                "conversation_history", []
            )

            migrated_history = []

            for item in previous_history:
                if isinstance(item, str):
                    user_text = ""
                    assistant_text = ""

                    if "User:" in item:
                        user_text = (
                            item.split("User:", 1)[1]
                            .split("Assistant:", 1)[0]
                            .strip()
                        )

                    if "Assistant:" in item:
                        assistant_text = item.split(
                            "Assistant:", 1
                        )[1].strip()

                    migrated_history.append({
                        "user": user_text,
                        "assistant": assistant_text,
                        "route": "",
                    })

                elif isinstance(item, dict):
                    migrated_history.append(item)

            initial_state["conversation_history"] = migrated_history[-5:]

        result = app.invoke(initial_state, config=config)

        history = list(result.get("conversation_history", []))

        current_turn = {
            "user": user_input,
            "assistant": result.get("final_response", ""),
            "route": result.get("route", ""),
        }

        if (
            history
            and isinstance(history[-1], dict)
            and history[-1].get("user", "").strip() == user_input
        ):
            history[-1] = current_turn
        else:
            history.append(current_turn)

        history = history[-5:]

        app.update_state(
            config,
            {"conversation_history": history},
        )

    # FINAL STATUS
    critique = str(result.get("critique", "")).strip().upper()

    verified = bool(
        re.search(r"\bSTATUS\s*:\s*PASS\b", critique)
    )

    if verified:
        final_status = "PASS"
    elif result.get("retry_count", 0) >= MAX_RETRIES:
        final_status = "RETRY LIMIT REACHED"
    else:
        final_status = "FAIL"

    # OUTPUT
    print("\n===== ORCHESTRATOR =====")
    print("Selected route:", result.get("route", ""))
    print(
        "Contextualized Query:",
        result.get("contextualized_query", user_input),
    )

    print("\n===== PLAN =====")
    plan = result.get("plan", [])

    if plan:
        for index, task in enumerate(plan, start=1):
            print(f"{index}. {task}")
    else:
        print("No plan was generated for this request.")

    print("\n===== CRITIC VERIFICATION =====")
    print("Final verification status:", final_status)
    print(result.get("critique", "No critic feedback available."))

    print("\n===== FINAL RESULT =====")
    print("STATUS:", final_status)
    print(result.get("final_response", "No final response was generated."))


# Run the CLI only when this file is executed directly.
# Importing app.main during pytest will not request user input.
if __name__ == "__main__":
    main()
