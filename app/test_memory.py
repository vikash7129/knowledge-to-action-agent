import os
import sys

from dotenv import load_dotenv


# ============================================================
# PROJECT SETUP
# ============================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(
        0,
        PROJECT_ROOT
    )

load_dotenv(
    os.path.join(
        PROJECT_ROOT,
        ".env"
    )
)


# ============================================================
# MEMORY TEST
# ============================================================

def run_memory_test():

    print("\n" + "=" * 60)
    print("STAGE 18.5 - MEMORY TEST")
    print("=" * 60)

    try:

        from app.agents.memory import update_memory

        print(
            "[PASS] Memory function import"
        )

        # ----------------------------------------------------
        # FIRST CONVERSATION
        # ----------------------------------------------------

        state = {
            "user_input": "What is Machine Learning?",
            "final_response": (
                "Machine Learning is a branch of AI "
                "that learns patterns from data."
            ),
            "route": "rag",
            "conversation_history": [],
        }

        result = update_memory(state)

        history = result.get(
            "conversation_history",
            []
        )

        if len(history) == 1:

            print(
                "[PASS] First conversation stored"
            )

        else:

            print(
                "[FAIL] First conversation not stored"
            )

            return False

        # ----------------------------------------------------
        # CHECK MEMORY FORMAT
        # ----------------------------------------------------

        first_item = history[0]

        if (
            isinstance(first_item, dict)
            and "user" in first_item
            and "assistant" in first_item
            and "route" in first_item
        ):

            print(
                "[PASS] Memory structure verified"
            )

        else:

            print(
                "[FAIL] Memory structure incorrect"
            )

            return False

        # ----------------------------------------------------
        # ADD MORE CONVERSATIONS
        # ----------------------------------------------------

        current_history = history

        for i in range(2, 8):

            state = {
                "user_input": f"Test question {i}",
                "final_response": f"Test answer {i}",
                "route": "planner",
                "conversation_history":
                    current_history,
            }

            result = update_memory(state)

            current_history = result.get(
                "conversation_history",
                []
            )

        # ----------------------------------------------------
        # CHECK LAST 5 LIMIT
        # ----------------------------------------------------

        if len(current_history) == 5:

            print(
                "[PASS] Memory limited to last 5 conversations"
            )

        else:

            print(
                "[FAIL] Memory limit incorrect:",
                len(current_history)
            )

            return False

        # ----------------------------------------------------
        # CHECK OLDEST MEMORY REMOVED
        # ----------------------------------------------------

        users = [
            item.get("user", "")
            for item in current_history
        ]

        if "What is Machine Learning?" not in users:

            print(
                "[PASS] Old memory correctly removed"
            )

        else:

            print(
                "[FAIL] Old memory was not removed"
            )

            return False

        # ----------------------------------------------------
        # FINAL STATUS
        # ----------------------------------------------------

        print("\n" + "=" * 60)
        print(
            "STAGE 18.5 STATUS: PASS"
        )
        print("=" * 60)

        return True

    except Exception as error:

        print(
            "\n[FAIL] MEMORY TEST"
        )

        print(
            "Error:",
            error
        )

        print("\n" + "=" * 60)
        print(
            "STAGE 18.5 STATUS: REVIEW REQUIRED"
        )
        print("=" * 60)

        return False


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    success = run_memory_test()

    raise SystemExit(
        0 if success else 1
    )