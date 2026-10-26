
import json
import os
import sqlite3
from datetime import datetime, timezone


DB_PATH = "memory.db"


def _summarize(value, limit=1500):
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        text = str(value)

    return text[:limit]


def trace_agent(agent_name, agent_function):
    """Wrap an agent and save its execution status in SQLite."""

    def traced_function(state):
        session_id = os.getenv("AGENT_THREAD_ID", "user-1")
        run_id = os.getenv("AGENT_TRACE_RUN_ID", "unknown-run")
        started_at = datetime.now(timezone.utc).isoformat()

        user_input = state.get("contextualized_query") or state.get("user_input", "")

        try:
            output = agent_function(state)

            output = output if isinstance(output, dict) else {}
            status = "success"
            error_message = ""

            summary_data = {
                "route": output.get("route", state.get("route", "")),
                "plan": output.get("plan", []),
                "results": output.get("results", []),
                "final_response": output.get("final_response", ""),
                "critique": output.get("critique", ""),
            }

        except Exception as exc:
            status = "error"
            error_message = str(exc)
            summary_data = {"error": error_message}
            raise

        finally:
            finished_at = datetime.now(timezone.utc).isoformat()

            try:
                with sqlite3.connect(DB_PATH, timeout=10) as conn:
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS execution_traces (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            session_id TEXT NOT NULL,
                            run_id TEXT NOT NULL,
                            agent_name TEXT NOT NULL,
                            input_summary TEXT,
                            status TEXT NOT NULL,
                            output_summary TEXT,
                            started_at TEXT NOT NULL,
                            finished_at TEXT NOT NULL
                        )
                    """)

                    conn.execute("""
                        INSERT INTO execution_traces (
                            session_id, run_id, agent_name,
                            input_summary, status, output_summary,
                            started_at, finished_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session_id,
                        run_id,
                        agent_name,
                        _summarize(user_input),
                        status,
                        _summarize(
                            summary_data if status == "success"
                            else {"error": error_message}
                        ),
                        started_at,
                        finished_at,
                    ))
            except Exception as trace_error:
                print(f"Tracing database warning: {trace_error}")

        return output

    return traced_function
