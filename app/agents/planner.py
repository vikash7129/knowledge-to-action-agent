
import re

from langchain_google_genai import ChatGoogleGenerativeAI
from .state import AgentState


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0
)


def planner_agent(state: AgentState):
    user_request = (
        state.get("contextualized_query")
        or state.get("user_input", "")
    )

    previous_feedback = state.get("critique", "").strip()
    retry_count = state.get("retry_count", 0)

    if retry_count > 0 and previous_feedback:
        improvement_instructions = f"""
This is a revised planning attempt.

The previous plan did not pass verification.
Carefully follow the critic's feedback and correct
the identified problems.

Previous critic feedback:
{previous_feedback}

Do not simply repeat the previous plan.
Make meaningful improvements.
"""
    else:
        improvement_instructions = """
Create an original plan that fully addresses the request.
"""

    prompt = f"""
You are an expert AI Project Planner.

User request:
{user_request}

{improvement_instructions}

Create a practical and specific plan.

Requirements:
1. Break the work into clear, actionable steps.
2. Include relevant technologies and tools.
3. Include implementation and testing.
4. Include evaluation and validation.
5. Consider important dependencies and potential risks.
6. Make the plan realistic and useful for a real AI portfolio project.
7. Avoid vague, duplicate, or irrelevant steps.
8. Ensure the revised plan addresses the critic's feedback.

Return ONLY a numbered list of actionable steps.
Do not include an introduction or conclusion.
"""

    response = llm.invoke(prompt)
    content = response.content

    if isinstance(content, str):
        response_text = content.strip()
    else:
        response_text = str(content).strip()

    tasks = []

    for line in response_text.splitlines():
        line = line.strip()

        if not line:
            continue

        # Remove numbering or bullet markers.
        line = re.sub(r"^\s*(?:\d+[\.\)]\s*|[-*•]\s*)", "", line)
        line = line.strip()

        if line:
            tasks.append(line)

    if not tasks:
        tasks = [
            "Clarify the requirements and define the project objectives.",
            "Choose suitable technologies and design the implementation.",
            "Implement the solution in manageable stages.",
            "Test the solution and fix identified issues.",
            "Evaluate the results and document the project."
        ]

    print("\n===== PLANNER AGENT =====")
    print("Planning attempt:", retry_count + 1)

    for index, task in enumerate(tasks, start=1):
        print(f"{index}. {task}")

    # Retry count is managed by critic_agent, not the planner.
    return {
        "plan": tasks
    }
