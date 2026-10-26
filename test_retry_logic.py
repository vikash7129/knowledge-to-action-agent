
from app.main import critic_router, MAX_RETRIES


def test_pass_routes_to_memory():
    state = {
        "critique": "STATUS: PASS\nFEEDBACK: Looks good.",
        "retry_count": 1,
        "route": "rag",
    }

    assert critic_router(state) == "pass"


def test_rag_fail_retries():
    state = {
        "critique": "STATUS: FAIL\nFEEDBACK: Improve grounding.",
        "retry_count": 1,
        "route": "rag",
    }

    assert critic_router(state) == "retry_rag"


def test_fail_at_retry_limit_stops():
    state = {
        "critique": "STATUS: FAIL\nFEEDBACK: Still unsupported.",
        "retry_count": MAX_RETRIES,
        "route": "rag",
    }

    assert critic_router(state) == "failed"


def test_planner_retries_same_agent():
    state = {
        "critique": "STATUS: FAIL\nFEEDBACK: Add implementation details.",
        "retry_count": 1,
        "route": "planner",
    }

    assert critic_router(state) == "retry_planner"


if __name__ == "__main__":
    test_pass_routes_to_memory()
    test_rag_fail_retries()
    test_fail_at_retry_limit_stops()
    test_planner_retries_same_agent()

    print("\nAll retry-routing tests passed.")
