import os
import sys
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv(
    os.path.join(
        PROJECT_ROOT,
        ".env"
    )
)


def run_executor_test():

    print("\n" + "=" * 60)
    print("STAGE 18.4 - EXECUTOR + RECOVERY TEST")
    print("=" * 60)

    try:

        from app.agents.executor import executor_agent

        print(
            "[PASS] Executor agent import"
        )

        # ----------------------------------------------------
        # SAFE CALCULATION
        # ----------------------------------------------------

        query = (
            "Calculate 25 * 4"
        )

        initial_state = {
            "user_input": query,
            "contextualized_query": query,
            "route": "executor",
            "plan": [],
            "results": [],
            "final_response": "",
            "critique": "",
            "retry_count": 0,
            "conversation_history": [],
            "execution_logs": [],
        }

        print(
            "[INFO] Query:",
            query
        )

        print(
            "[INFO] Running Executor..."
        )

        result = executor_agent(
            initial_state
        )

        print("\n" + "-" * 60)
        print("EXECUTOR RESULT")
        print("-" * 60)

        final_response = result.get(
            "final_response",
            ""
        )

        if not final_response:

            print(
                "[FAIL] Executor returned empty response"
            )

            return False

        print(
            "[PASS] Executor returned a response"
        )

        print(
            "Final response:",
            final_response
        )

        # ----------------------------------------------------
        # CHECK CALCULATION RESULT
        # ----------------------------------------------------

        if "100" in str(final_response):

            print(
                "[PASS] Calculator execution verified"
            )

        else:

            print(
                "[FAIL] Expected calculation result 100"
            )

            return False

        # ----------------------------------------------------
        # RECOVERY FUNCTION TEST
        # ----------------------------------------------------

        from app.agents.error_handler import (
            create_recovery_response,
        )

        recovery_state = {
            "retry_count": 0,
            "final_response": "",
            "critique": "",
            "results": [],
        }

        recovery_result = (
            create_recovery_response(
                recovery_state,
                "Test recovery error"
            )
        )

        new_retry_count = recovery_result.get(
            "retry_count",
            -1
        )

        if new_retry_count == 1:

            print(
                "[PASS] Recovery retry count updated"
            )

        else:

            print(
                "[FAIL] Recovery retry count incorrect"
            )

            return False

        recovery_message = (
            recovery_result.get(
                "final_response",
                ""
            )
        )

        if recovery_message:

            print(
                "[PASS] Recovery response generated"
            )

        else:

            print(
                "[FAIL] Recovery response empty"
            )

            return False

        print("\n" + "=" * 60)
        print(
            "STAGE 18.4 STATUS: PASS"
        )
        print("=" * 60)

        return True

    except Exception as error:

        print(
            "\n[FAIL] EXECUTOR + RECOVERY TEST"
        )

        print(
            "Error:",
            error
        )

        print("\n" + "=" * 60)
        print(
            "STAGE 18.4 STATUS: REVIEW REQUIRED"
        )
        print("=" * 60)

        return False


if __name__ == "__main__":

    success = run_executor_test()

    raise SystemExit(
        0 if success else 1
    )