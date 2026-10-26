import os

from tavily import TavilyClient
from langchain_google_genai import (
    ChatGoogleGenerativeAI
)

from .state import AgentState


# =========================
# GEMINI LLM
# =========================

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.2
)


# =========================
# TAVILY API KEY
# =========================

tavily_api_key = os.getenv(
    "TAVILY_API_KEY"
)

if not tavily_api_key:

    raise ValueError(
        "TAVILY_API_KEY is missing. "
        "Please add it to your .env file."
    )


# =========================
# TAVILY CLIENT
# =========================

tavily = TavilyClient(
    api_key=tavily_api_key
)


# =========================
# RESEARCHER AGENT
# =========================

def researcher_agent(
    state: AgentState
):

    # =========================
    # USER QUERY
    # =========================

    query = state.get(
        "contextualized_query",
        state["user_input"]
    )

    # =========================
    # WEB SEARCH
    # =========================

    print(
        "\n===== RESEARCHER ====="
    )

    print(
        "Research Query:",
        query
    )

    search_result = tavily.search(
        query=query,
        search_depth="basic",
        max_results=5
    )

    # =========================
    # SEARCH RESULTS
    # =========================

    sources = search_result.get(
        "results",
        []
    )

    print(
        "Sources Found:",
        len(sources)
    )

    # =========================
    # NO RESULTS
    # =========================

    if not sources:

        final_response = (
            "I could not find relevant "
            "web sources for this query."
        )

        return {
            "results": [final_response],
            "final_response": final_response
        }

    # =========================
    # PREPARE RESEARCH CONTEXT
    # =========================

    research_context = ""

    source_list = []

    for index, source in enumerate(
        sources,
        start=1
    ):

        title = source.get(
            "title",
            ""
        )

        content = source.get(
            "content",
            ""
        )

        url = source.get(
            "url",
            ""
        )

        research_context += f"""
SOURCE {index}

Title:
{title}

Content:
{content}

URL:
{url}

-------------------------
"""

        source_list.append(
            {
                "title": title,
                "url": url
            }
        )

    # =========================
    # RESEARCH PROMPT
    # =========================

    prompt = f"""
You are a reliable Research Agent.

User request:
{query}

Use ONLY the web search results
provided below.

WEB SEARCH RESULTS:
{research_context}

Instructions:

1. Answer the user's request clearly.
2. Use information from the provided
   search results.
3. Do not invent facts.
4. If the search results do not provide
   enough information, say so clearly.
5. Prefer information supported by
   multiple sources when possible.
6. Keep the answer concise but useful.
7. At the end, provide a Sources section.
8. Do not create or modify URLs.
9. Use only URLs provided in the
   search results.

Format:

Answer:
<research answer>

Sources:
- <source title> — <URL>
"""

    # =========================
    # GENERATE ANSWER
    # =========================

    response = llm.invoke(
        prompt
    )

    final_response = str(
        response.content
    ).strip()

    # =========================
    # SAFETY FALLBACK
    # =========================

    if not final_response:

        final_response = (
            "The research agent could not "
            "generate a response from the "
            "available web sources."
        )

    # =========================
    # RETURN
    # =========================

    return {
        "results": [
            final_response
        ],
        "final_response":
            final_response
    }