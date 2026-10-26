import os
import sys
from dotenv import load_dotenv

# Project root
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Load .env
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


def run_rag_test():
    print("\n" + "=" * 60)
    print("STAGE 18.2 - RAG END-TO-END TEST")
    print("=" * 60)

    try:
        from app.agents.rag_agent import rag_agent

        print("[PASS] RAG agent import")

        # Known document query from our RAG test data
        query = "What is Reinforcement Learning?"

        initial_state = {
            "user_input": query,
            "contextualized_query": query,
            "route": "rag",
            "plan": [],
            "results": [],
            "final_response": "",
            "critique": "",
            "retry_count": 0,
            "conversation_history": [],
            "execution_logs": [],
        }

        print("[INFO] Query:", query)
        print("[INFO] Running RAG pipeline...")

        result = rag_agent(initial_state)

        print("\n" + "-" * 60)
        print("RAG RESULT")
        print("-" * 60)

        final_response = result.get("final_response", "")

        if final_response:
            print("[PASS] RAG generated a response")
            print("\nAnswer:")
            print(final_response)
        else:
            print("[FAIL] RAG returned an empty response")
            return False

        # Check retrieved results
        results = result.get("results", [])

        if results:
            print("\n[PASS] Retrieved document context")
            print("Retrieved items:", len(results))
        else:
            print("\n[WARN] No results found in state")

        # Basic grounding check
        response_text = str(final_response).lower()

        if (
            "reinforcement" in response_text
            or "reward" in response_text
            or "penalty" in response_text
        ):
            print("[PASS] Response appears grounded to the RAG query")
        else:
            print("[WARN] Response does not contain expected RAG keywords")

        print("\n" + "=" * 60)
        print("STAGE 18.2 STATUS: PASS")
        print("=" * 60)

        return True

    except Exception as error:
        print("\n[FAIL] RAG END-TO-END TEST")
        print("Error:", error)

        print("\n" + "=" * 60)
        print("STAGE 18.2 STATUS: REVIEW REQUIRED")
        print("=" * 60)

        return False


if __name__ == "__main__":
    success = run_rag_test()
    raise SystemExit(0 if success else 1)