
import re

from langchain_google_genai import ChatGoogleGenerativeAI
from .state import AgentState


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
)


def get_response_text(response):
    content = response.content

    if isinstance(content, str):
        return content.strip()

    return str(content).strip()


def critic_agent(state: AgentState):
    route = state.get("route", "")

    user_input = (
        state.get("contextualized_query")
        or state.get("user_input", "")
    )

    answer = state.get("final_response", "")
    results = state.get("results", [])
    plan = state.get("plan", [])
    previous_critique = state.get("critique", "")
    retry_count = state.get("retry_count", 0) + 1

    if route == "rag":
        evidence_blocks = []

        for index, item in enumerate(results, start=1):
            if isinstance(item, dict):
                content = item.get("content", "")
                source = item.get("source", "Unknown source")
                page = item.get("page")

                evidence_blocks.append(
                    f"Evidence {index}\n"
                    f"Source: {source}\n"
                    f"Page: {page if page is not None else 'Not available'}\n"
                    f"Content:\n{content}"
                )
            else:
                # Backward compatibility with older string results.
                evidence_blocks.append(
                    f"Evidence {index}\n{item}"
                )

        retrieved_evidence = (
            "\n\n".join(evidence_blocks)
            if evidence_blocks
            else "No retrieved evidence is available."
        )

        prompt = f"""
You are an evidence-based RAG verification agent.

User question:
{user_input}

Generated answer:
{answer}

Actual retrieved document evidence:
{retrieved_evidence}

Previous critic feedback:
{previous_critique or "No previous feedback."}

Verification attempt:
{retry_count}

Check:
1. Does the answer address the user's question?
2. Are its document-based factual claims supported by the evidence?
3. Does it avoid claims that the evidence does not establish?
4. Are the listed sources consistent with the retrieved evidence?
5. If evidence is missing or insufficient, does the answer acknowledge
   this limitation instead of inventing information?
6. If this is a retry, was the previous feedback addressed?

Rules:
- Do not treat a source filename alone as evidence for a claim.
- Check the actual retrieved content.
- Do not assume an answer is correct merely because it sounds plausible.
- PASS only if the answer is sufficiently relevant and supported.
- FAIL if there is a meaningful unsupported claim or other important issue.
- Be fair about minor wording issues.
- Do not claim that a citation is verified if its supporting evidence
  is absent.

Return exactly:
STATUS: PASS
FEEDBACK: Short explanation

OR

STATUS: FAIL
FEEDBACK: Specific correction instructions
"""

    else:
        prompt = f"""
You are a strict but fair AI agent critic.

User request:
{user_input}

Selected route:
{route}

Generated plan:
{plan}

Generated result:
{answer}

Previous critic feedback:
{previous_critique or "No previous feedback."}

Verification attempt:
{retry_count}

Check:
1. Does the result address the request?
2. Is it clear and useful?
3. Is the plan practical and specific when required?
4. Was previous feedback addressed on a retry?
5. Are there meaningful errors or unsupported claims?

Return PASS only when the result is good enough.
Do not fail a useful answer for minor stylistic issues.

Return exactly:
STATUS: PASS
FEEDBACK: Short explanation

OR

STATUS: FAIL
FEEDBACK: Specific correction instructions
"""

    response = llm.invoke(prompt)
    critique = get_response_text(response)

    status_match = re.search(
        r"^\s*STATUS\s*:\s*(PASS|FAIL)\s*$",
        critique,
        re.IGNORECASE | re.MULTILINE,
    )

    if status_match is None:
        critique = (
            "STATUS: FAIL\n"
            "FEEDBACK: Invalid critic status. Review the result "
            "and retry verification."
        )
    else:
        status = status_match.group(1).upper()
        critique = re.sub(
            r"^\s*STATUS\s*:\s*(PASS|FAIL)\s*$",
            f"STATUS: {status}",
            critique,
            count=1,
            flags=re.IGNORECASE | re.MULTILINE,
        )

    print("\n===== CRITIC AGENT =====")
    print("Attempt:", retry_count)
    print(critique)

    return {
        "critique": critique,
        "retry_count": retry_count,
    }
