import os
import sys
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


def run_researcher_test():
    print("\n" + "=" * 60)
    print("STAGE 18.3 - RESEARCHER END-TO-END TEST")
    print("=" * 60)

    try:
        from app.agents.researcher import researcher_agent

        print("[PASS] Researcher agent import")

        query = "What is Retrieval Augmented Generation?"

        initial_state = {
            "user_input": query,
            "contextualized_query": query,
            "route": "researcher",
            "plan": [],
            "results": [],
            "final_response": "",
            "critique": "",
            "retry_count": 0,
            "conversation_history": [],
            "execution_logs": [],
        }

        print("[INFO] Query:", query)
        print("[INFO] Running Researcher + Tavily...")

        result = researcher_agent(initial_state)

        print("\n" + "-" * 60)
        print("RESEARCHER RESULT")
        print("-" * 60)

        results = result.get("results", [])

        if results:
            print("[PASS] Research results received")
            print("Result items:", len(results))
        else:
            print("[FAIL] No research results returned")
            return False

        print("\nResearch output:")
        for item in results[:3]:
            print("\n", item)

        print("\n" + "=" * 60)
        print("STAGE 18.3 STATUS: PASS")
        print("=" * 60)

        return True

    except Exception as error:
        print("\n[FAIL] RESEARCHER END-TO-END TEST")
        print("Error:", error)

        print("\n" + "=" * 60)
        print("STAGE 18.3 STATUS: REVIEW REQUIRED")
        print("=" * 60)

        return False


if __name__ == "__main__":
    success = run_researcher_test()
    raise SystemExit(0 if success else 1)