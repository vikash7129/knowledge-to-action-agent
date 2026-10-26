import os
import sys

from dotenv import load_dotenv


# ============================================================
# PROJECT SETUP
# ============================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
    )
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# IMPORTANT:
# Load .env BEFORE importing any agent that creates an LLM.
load_dotenv(
    os.path.join(
        PROJECT_ROOT,
        ".env",
    )
)


# ============================================================
# SECURITY TEST
# ============================================================

def test_security():

    from app.security import (
        validate_required_secrets,
    )

    from app.tools.registry import (
        validate_registry,
        list_available_tools,
    )

    from app.tools.calculator import (
        calculator,
    )

    from app.tools.python_tool import (
        run_python,
        validate_code,
    )

    # --------------------------------------------------------
    # Environment secrets
    # --------------------------------------------------------

    secrets_valid, missing = (
        validate_required_secrets()
    )

    if not secrets_valid:
        return False, (
            "Missing environment secrets: "
            + ", ".join(missing)
        )

    # --------------------------------------------------------
    # Tool registry
    # --------------------------------------------------------

    registry_valid, errors = (
        validate_registry()
    )

    if not registry_valid:
        return False, (
            "Tool registry failed: "
            + "; ".join(errors)
        )

    # --------------------------------------------------------
    # Available tools
    # --------------------------------------------------------

    tools = list_available_tools()

    if "calculator" not in tools:
        return False, (
            "Calculator tool unavailable."
        )

    if "python" not in tools:
        return False, (
            "Python tool unavailable."
        )

    # --------------------------------------------------------
    # Calculator
    # --------------------------------------------------------

    if calculator("25 * 4 + 10") != "110":
        return False, (
            "Calculator test failed."
        )

    # --------------------------------------------------------
    # Python
    # --------------------------------------------------------

    if run_python(
        "result = 25 * 4"
    ) != "100":

        return False, (
            "Python tool test failed."
        )

    # --------------------------------------------------------
    # Unsafe Python
    # --------------------------------------------------------

    valid, _ = validate_code(
        "import os"
    )

    if valid:
        return False, (
            "Unsafe Python import was accepted."
        )

    return True, (
        "Security layer passed."
    )


# ============================================================
# PROJECT STRUCTURE TEST
# ============================================================

def test_project_structure():

    required_paths = [
        "app/main.py",
        "app/streamlit_app.py",

        # Agent files
        "app/agents/state.py",
        "app/agents/orchestrator.py",
        "app/agents/planner.py",
        "app/agents/researcher.py",
        "app/agents/executor.py",
        "app/agents/critic.py",
        "app/agents/rag_agent.py",
        "app/agents/error_handler.py",

        # RAG
        "app/rag/loader.py",
        "app/rag/retriever.py",

        # Tools
        "app/tools/calculator.py",
        "app/tools/python_tool.py",
        "app/tools/registry.py",

        # Security
        "app/security.py",
        "app/security_review.py",
    ]

    missing = []

    for relative_path in required_paths:

        full_path = os.path.join(
            PROJECT_ROOT,
            relative_path,
        )

        if not os.path.isfile(full_path):
            missing.append(relative_path)

    if missing:

        return False, (
            "Missing project files: "
            + ", ".join(missing)
        )

    return True, (
        "Required project structure is present."
    )


# ============================================================
# RAG STRUCTURE TEST
# ============================================================

def test_rag_structure():

    data_directory = os.path.join(
        PROJECT_ROOT,
        "data",
    )

    uploads_directory = os.path.join(
        data_directory,
        "uploads",
    )

    if not os.path.isdir(
        data_directory
    ):
        return False, (
            "data/ directory is missing."
        )

    if not os.path.isdir(
        uploads_directory
    ):
        return False, (
            "data/uploads/ directory is missing."
        )

    return True, (
        "RAG data directories are available."
    )


# ============================================================
# AGENT IMPORT TEST
# ============================================================

def test_agent_imports():

    try:

        from app.agents.state import AgentState
        from app.agents.orchestrator import (
            orchestrator_agent,
        )
        from app.agents.planner import (
            planner_agent,
        )
        from app.agents.researcher import (
            researcher_agent,
        )
        from app.agents.executor import (
            executor_agent,
        )
        from app.agents.critic import (
            critic_agent,
        )
        from app.agents.rag_agent import (
            rag_agent,
        )

        _ = (
            AgentState,
            orchestrator_agent,
            planner_agent,
            researcher_agent,
            executor_agent,
            critic_agent,
            rag_agent,
        )

        return True, (
            "All core agents imported successfully."
        )

    except Exception as error:

        return False, (
            "Agent import failed: "
            + str(error)
        )


# ============================================================
# FINAL TEST RUNNER
# ============================================================

def run_final_system_test():

    tests = [
        (
            "Project structure",
            test_project_structure,
        ),
        (
            "Agent imports",
            test_agent_imports,
        ),
        (
            "RAG structure",
            test_rag_structure,
        ),
        (
            "Security layer",
            test_security,
        ),
    ]

    passed = 0
    total = len(tests)

    print("\n" + "=" * 60)
    print("KNOWLEDGE-TO-ACTION AGENT")
    print("FINAL SYSTEM TEST")
    print("=" * 60)

    for test_name, test_function in tests:

        try:

            success, message = test_function()

        except Exception as error:

            success = False
            message = (
                f"Unexpected error: {error}"
            )

        status = (
            "PASS"
            if success
            else "FAIL"
        )

        print(
            f"[{status}] "
            f"{test_name}: "
            f"{message}"
        )

        if success:
            passed += 1

    print("=" * 60)
    print(
        f"Tests passed: {passed}/{total}"
    )

    if passed == total:

        print(
            "FINAL SYSTEM STATUS: PASS"
        )

        return True

    print(
        "FINAL SYSTEM STATUS: REVIEW REQUIRED"
    )

    return False


# ============================================================
# DIRECT EXECUTION
# ============================================================

if __name__ == "__main__":

    success = run_final_system_test()

    raise SystemExit(
        0 if success else 1
    )