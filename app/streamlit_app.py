
import html
import os
import re
import subprocess
import sys
import uuid
import hashlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from app.rag.ingest import ingest_document


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"
MAX_HISTORY_ITEMS = 20


st.set_page_config(
    page_title="Knowledge-to-Action Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CUSTOM DARK UI
# ============================================================

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at 10% 0%,
                rgba(79, 103, 190, 0.15), transparent 34%),
            radial-gradient(circle at 95% 8%,
                rgba(130, 75, 180, 0.12), transparent 30%),
            #080b12;
        color: #f3f5fb;
    }

    .block-container {
        max-width: 1150px;
        padding-top: 1.6rem;
        padding-bottom: 5rem;
    }

    section[data-testid="stSidebar"] {
        background: #0b0f18;
        border-right: 1px solid rgba(255,255,255,0.07);
    }

    .hero {
        padding: 25px 28px;
        margin-bottom: 20px;
        border-radius: 22px;
        background: linear-gradient(
            135deg,
            rgba(27, 34, 56, 0.98),
            rgba(14, 18, 30, 0.98)
        );
        border: 1px solid rgba(255,255,255,0.09);
        box-shadow: 0 18px 45px rgba(0,0,0,0.22);
    }

    .hero-title {
        font-size: clamp(25px, 3vw, 35px);
        font-weight: 800;
        letter-spacing: -1px;
        margin-bottom: 7px;
    }

    .hero-subtitle {
        color: #a5aec1;
        font-size: 14px;
        line-height: 1.7;
    }

    .eyebrow {
        color: #9aa8ff;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1.6px;
        font-weight: 750;
        margin-bottom: 8px;
    }

    .metric-card {
        background: rgba(18, 24, 38, 0.88);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 14px;
        padding: 14px 15px;
        min-height: 88px;
    }

    .metric-label {
        color: #939db1;
        font-size: 12px;
        margin-bottom: 7px;
    }

    .metric-value {
        color: #f3f5fb;
        font-size: 17px;
        font-weight: 750;
    }

    .sidebar-note {
        color: #929db2;
        font-size: 12px;
        line-height: 1.7;
    }

    .status-pill {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 30px;
        background: rgba(115, 140, 255, 0.12);
        border: 1px solid rgba(115, 140, 255, 0.25);
        color: #b9c5ff;
        font-size: 12px;
        font-weight: 700;
    }

    .source-card {
        background: #101624;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 11px;
        padding: 11px 13px;
        margin-bottom: 8px;
        overflow-wrap: anywhere;
    }

    .footer {
        color: #69758a;
        text-align: center;
        font-size: 12px;
        padding: 22px 0 8px;
    }

    div[data-testid="stChatMessage"] {
        border: 1px solid rgba(255,255,255,0.045);
        border-radius: 16px;
        padding: 12px 15px;
        margin-bottom: 12px;
        background: rgba(17, 22, 34, 0.54);
    }

    div[data-testid="stChatInput"] {
        border-color: rgba(140, 155, 220, 0.32);
    }

    .stButton > button {
        border-radius: 11px;
        min-height: 40px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================

def create_conversation():
    conversation_id = uuid.uuid4().hex

    return conversation_id, {
        "title": "New Chat",
        "messages": [],
    }


if "documents" not in st.session_state:
    st.session_state.documents = []

if "conversations" not in st.session_state:
    conversation_id, conversation = create_conversation()
    st.session_state.conversations = {
        conversation_id: conversation
    }
    st.session_state.current_conversation_id = conversation_id

if "current_conversation_id" not in st.session_state:
    conversation_id, conversation = create_conversation()
    st.session_state.conversations[conversation_id] = conversation
    st.session_state.current_conversation_id = conversation_id

if st.session_state.current_conversation_id not in st.session_state.conversations:
    conversation_id, conversation = create_conversation()
    st.session_state.conversations[conversation_id] = conversation
    st.session_state.current_conversation_id = conversation_id

# The backend uses this ID for conversation memory/checkpointing.
st.session_state.agent_thread_id = st.session_state.current_conversation_id


# ============================================================
# OUTPUT PARSING HELPERS
# ============================================================

def safe_text(value):
    return html.escape(str(value))



def extract_section(output, section_name):
    """Extract a named section between ===== SECTION ===== headers."""

    if not output:
        return ""

    header_pattern = r"={3,}\s*([^=\r\n]+?)\s*={3,}"

    matches = list(re.finditer(header_pattern, output))

    for index, match in enumerate(matches):
        header_name = match.group(1).strip()

        if header_name.casefold() != section_name.casefold():
            continue

        section_start = match.end()

        if index + 1 < len(matches):
            section_end = matches[index + 1].start()
        else:
            section_end = len(output)

        return output[section_start:section_end].strip()

    return ""



def extract_route(output):
    patterns = [
        r"Selected route\s*:\s*([A-Za-z0-9_-]+)",
        r"Route\s*:\s*([A-Za-z0-9_-]+)",
        r"selected_route\s*=\s*([A-Za-z0-9_-]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, output or "", re.IGNORECASE)
        if match:
            return match.group(1).strip().lower()

    return ""


def extract_field(text, field_names):
    if not text:
        return ""

    for field in field_names:
        pattern = rf"^\s*{re.escape(field)}\s*:\s*(.+)$"

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )

        if match:
            return match.group(1).strip()

    return ""


def extract_critic_status(output):
    sections = [
        extract_section(output, "CRITIC VERIFICATION"),
        extract_section(output, "CRITIC"),
    ]

    for section in sections:
        if not section:
            continue

        match = re.search(
            r"(?:Final verification status|Verification status|Status)"
            r"\s*:\s*(PASS|FAIL|ERROR)",
            section,
            re.IGNORECASE,
        )

        if match:
            return match.group(1).upper()

    # Also check the full output for a printed verification status.
    match = re.search(
        r"Final verification status\s*:\s*(PASS|FAIL|ERROR)",
        output or "",
        re.IGNORECASE,
    )

    return match.group(1).upper() if match else ""


def extract_urls(text):
    urls = re.findall(
        r"https?://[^\s<>\]\)\"']+",
        text or "",
        flags=re.IGNORECASE,
    )

    result = []

    for url in urls:
        url = url.rstrip(".,;:")
        if url not in result:
            result.append(url)

    return result


def extract_source_lines(section):
    lines = []

    for line in (section or "").splitlines():
        cleaned = line.strip()

        if not cleaned:
            continue

        lower = cleaned.lower()

        if (
            "source" in lower
            or "http://" in lower
            or "https://" in lower
            or "url:" in lower
            or "title:" in lower
        ):
            if cleaned not in lines:
                lines.append(cleaned)

    return lines


def extract_answer(section):
    if not section:
        return ""

    labels = [
        "Final Answer",
        "Final Response",
        "Research Answer",
        "RAG Answer",
        "Answer",
    ]

    for label in labels:
        pattern = rf"{re.escape(label)}\s*:\s*(.*)"

        match = re.search(
            pattern,
            section,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if match:
            return match.group(1).strip()

    return ""


def extract_final_response(output):
    """
    Prefer the backend's FINAL RESULT section.
    Fall back to the selected agent's answer when needed.
    """

    final_section = extract_section(output, "FINAL RESULT")

    if final_section:
        final_section = re.sub(
            r"^\s*STATUS\s*:\s*[A-Z_ -]+\s*$",
            "",
            final_section,
            flags=re.IGNORECASE | re.MULTILINE,
        ).strip()

        if final_section:
            return final_section

    for section_name in [
        "RAG",
        "RAG AGENT",
        "RESEARCHER",
        "EXECUTOR",
        "PLANNER",
    ]:
        section = extract_section(output, section_name)
        answer = extract_answer(section)

        if answer:
            return answer

    return (
        "The agent finished, but a clearly labelled final answer "
        "could not be extracted from the backend output. "
        "Open the execution logs below to inspect the response."
    )


def detect_execution_error(output, return_code):
    if return_code != 0:
        return True

    error_patterns = [
        "Traceback (most recent call last)",
        "ModuleNotFoundError:",
        "ImportError:",
        "SyntaxError:",
        "NameError:",
        "TypeError:",
        "ValueError:",
        "RuntimeError:",
        "Application error:",
        "timed out",
    ]

    return any(
        pattern.lower() in (output or "").lower()
        for pattern in error_patterns
    )


def get_message_details(output, return_code):
    route = extract_route(output)
    critic_status = extract_critic_status(output)
    failed = detect_execution_error(output, return_code)

    if failed:
        status = "ERROR"
    elif critic_status:
        status = critic_status
    else:
        status = "COMPLETED"

    if route in {"rag", "researcher"}:
        section = extract_section(output, route.upper())

        if not section and route == "rag":
            section = extract_section(output, "RAG AGENT")
    else:
        section = ""

    source_lines = extract_source_lines(section)
    urls = extract_urls(section)

    # De-duplicate the source list.
    sources = list(dict.fromkeys(source_lines + urls))

    query = extract_field(
        output,
        [
            "Contextualized Query",
            "Search Query",
            "RAG Query",
        ],
    )

    return {
        "route": route or "unknown",
        "status": status,
        "critic_status": critic_status or "Not reported",
        "sources": sources,
        "query": query,
        "output": output,
        "return_code": return_code,
    }


# ============================================================
# BACKEND EXECUTION
# ============================================================

def run_agent(prompt, thread_id):
    environment = os.environ.copy()
    environment["AGENT_THREAD_ID"] = thread_id

    existing_pythonpath = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = (
        str(PROJECT_ROOT)
        + (os.pathsep + existing_pythonpath if existing_pythonpath else "")
    )

    try:
        process = subprocess.run(
            [sys.executable, "-m", "app.main"],
            input=prompt.strip() + "\n",
            text=True,
            capture_output=True,
            timeout=180,
            cwd=str(PROJECT_ROOT),
            env=environment,
        )

        output = (
            (process.stdout or "")
            + "\n"
            + (process.stderr or "")
        ).strip()

        if not output:
            output = "The backend returned no output."

        return output, process.returncode

    except subprocess.TimeoutExpired:
        return "Agent execution timed out after 180 seconds.", 1

    except Exception as error:
        return f"Application error: {error}", 1


# ============================================================
# CHAT MESSAGE DETAILS
# ============================================================

def render_pipeline(route):
    nodes = [
        ("🧠", "Orchestrator"),
        ("📋", "Planner"),
        ("🔎", "Researcher"),
        ("🛠️", "Executor"),
        ("📚", "RAG"),
        ("🧐", "Critic"),
        ("💾", "Memory"),
    ]

    active_map = {
        "planner": "Planner",
        "researcher": "Researcher",
        "executor": "Executor",
        "rag": "RAG",
    }

    active_node = active_map.get(route, "")

    cols = st.columns(len(nodes))

    for col, (emoji, name) in zip(cols, nodes):
        with col:
            if name == active_node:
                st.markdown(f"**🔹 {emoji} {name}**")
            else:
                st.caption(f"{emoji} {name}")


def render_message_details(details):
    if not details:
        return

    route = details.get("route", "unknown")
    status = details.get("status", "COMPLETED")
    output = details.get("output", "")
    return_code = details.get("return_code", 0)

    with st.expander("🧭 Execution details", expanded=False):
        metric1, metric2, metric3 = st.columns(3)

        metric1.metric("Selected route", route.upper())
        metric2.metric("Execution status", status)
        metric3.metric("Exit code", return_code)

        st.markdown("**Agent pipeline**")
        render_pipeline(route)

        critic_status = details.get("critic_status", "Not reported")
        st.markdown(f"**Critic verification:** {critic_status}")

        query = details.get("query", "")
        if query:
            st.markdown("**Contextualized query**")
            st.write(query)

        sources = details.get("sources", [])
        st.markdown("**Sources and references**")

        if sources:
            for index, source in enumerate(sources, start=1):
                st.markdown(
                    f'<div class="source-card">'
                    f'<strong>Source {index}</strong><br>'
                    f'{safe_text(source)}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption(
                "No explicit source entries were detected in this output."
            )

        plan = extract_section(output, "PLAN")
        if not plan:
            plan = extract_section(output, "PLANNER")

        if plan:
            with st.expander("📋 Agent plan"):
                st.code(plan, language="text")

        critic = extract_section(output, "CRITIC VERIFICATION")
        if not critic:
            critic = extract_section(output, "CRITIC")

        if critic:
            with st.expander("🧐 Critic analysis"):
                st.code(critic, language="text")

        recovery = extract_section(output, "EXECUTOR RECOVERY")
        if recovery:
            with st.expander("🛡️ Recovery details"):
                st.code(recovery, language="text")

        with st.expander("🧾 Raw execution logs"):
            st.code(output, language="text")


# ============================================================
# SIDEBAR: CHAT HISTORY AND DOCUMENTS
# ============================================================

with st.sidebar:
    st.markdown("## 🤖 Knowledge Agent")
    st.caption("Your multi-agent AI workspace")

    if st.button("＋  New Chat", use_container_width=True, type="primary"):
        conversation_id, conversation = create_conversation()
        st.session_state.conversations[conversation_id] = conversation
        st.session_state.current_conversation_id = conversation_id
        st.session_state.agent_thread_id = conversation_id
        st.rerun()

    st.divider()
    st.markdown("### 💬 Recent conversations")

    conversations = st.session_state.conversations
    current_id = st.session_state.current_conversation_id

    history_items = list(conversations.items())[::-1][:MAX_HISTORY_ITEMS]

    if not history_items:
        st.caption("Your conversations will appear here.")

    for conversation_id, conversation in history_items:
        title = conversation.get("title", "New Chat")
        is_current = conversation_id == current_id
        button_label = ("● " if is_current else "○ ") + title[:35]

        if st.button(
            button_label,
            key=f"history_{conversation_id}",
            use_container_width=True,
        ):
            st.session_state.current_conversation_id = conversation_id
            st.session_state.agent_thread_id = conversation_id
            st.rerun()

    
    
    st.divider()
    st.markdown("### 📚 Knowledge base")
    st.caption(
        "Upload PDF or TXT files. New or changed files are "
        "automatically indexed in ChromaDB."
    )

    uploaded_files = st.file_uploader(
        "Upload PDF / TXT",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        key="knowledge_upload",
    )

    if "indexed_upload_hashes" not in st.session_state:
        st.session_state.indexed_upload_hashes = {}

    if uploaded_files:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        for uploaded_file in uploaded_files:
            filename = Path(uploaded_file.name).name
            file_path = UPLOAD_DIR / filename
            content = uploaded_file.getvalue()
            content_hash = hashlib.sha256(content).hexdigest()

            # Skip only if this exact content was indexed
            # successfully during the current Streamlit session.
            if (
                st.session_state.indexed_upload_hashes.get(filename)
                == content_hash
            ):
                st.success(f"{filename}: already indexed.")
                continue

            try:
                file_path.write_bytes(content)

                with st.spinner(f"Indexing {filename}..."):
                    chunk_count = ingest_document(str(file_path))

                st.session_state.indexed_upload_hashes[filename] = (
                    content_hash
                )

                if filename not in st.session_state.documents:
                    st.session_state.documents.append(filename)

                st.success(
                    f"Indexed {filename} successfully "
                    f"({chunk_count} chunks)."
                )

            except Exception as error:
                st.error(
                    f"Could not index {filename}: "
                    f"{type(error).__name__}: {error}"
                )

    if st.session_state.documents:
        st.markdown("**Uploaded in this session**")
        for document in st.session_state.documents:
            st.caption(f"📄 {document}")

    st.divider()



    if st.button("🧹 Clear current chat", use_container_width=True):
        conversation_id = st.session_state.current_conversation_id

        st.session_state.conversations[conversation_id] = {
            "title": "New Chat",
            "messages": [],
        }

        # A fresh thread ID prevents old backend memory from being reused.
        new_id = uuid.uuid4().hex
        st.session_state.conversations[new_id] = {
            "title": "New Chat",
            "messages": [],
        }
        st.session_state.current_conversation_id = new_id
        st.session_state.agent_thread_id = new_id
        st.rerun()

    st.markdown(
        """
        <div class="sidebar-note">
            <br>
            <b>System modules</b><br>
            Orchestrator · Planner · Researcher<br>
            Executor · RAG · Critic · Memory
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# MAIN HEADER
# ============================================================

st.markdown(
    """
    <div class="hero">
        <div class="eyebrow">AI workspace · Multi-agent system</div>
        <div class="hero-title">Knowledge-to-Action Agent</div>
        <div class="hero-subtitle">
            Ask questions, research information, reason over your documents,
            execute supported tools, and inspect how the agent reached its result.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

metric_columns = st.columns(4)

metric_values = [
    ("Architecture", "Multi-Agent"),
    ("Knowledge", "RAG Enabled"),
    ("Research", "Tavily"),
    ("Verification", "Critic"),
]

for column, (label, value) in zip(metric_columns, metric_values):
    with column:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">{safe_text(label)}</div>
                <div class="metric-value">{safe_text(value)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.write("")


# ============================================================
# CHAT HISTORY DISPLAY
# ============================================================

current_id = st.session_state.current_conversation_id
current_conversation = st.session_state.conversations[current_id]

st.markdown(
    '<div class="eyebrow">Conversation</div>',
    unsafe_allow_html=True,
)

if not current_conversation["messages"]:
    st.markdown("### 👋 What would you like to work on?")
    st.caption(
        "Ask a question, request research, calculate something, "
        "or ask about information in your knowledge base."
    )

    example_columns = st.columns(3)

    examples = [
        "Calculate 25 * 4",
        "Explain machine learning",
        "Research recent AI developments",
    ]

    for column, example in zip(example_columns, examples):
        with column:
            if st.button(
                example,
                key=f"example_{current_id}_{example}",
                use_container_width=True,
            ):
                st.session_state.pending_prompt = example
                st.rerun()

for message in current_conversation["messages"]:
    role = message.get("role", "assistant")

    with st.chat_message(
        "user" if role == "user" else "assistant",
        avatar="🧑‍💻" if role == "user" else "🤖",
    ):
        st.markdown(message.get("content", ""))

        if role == "assistant":
            render_message_details(message.get("details"))


# ============================================================
# CHAT INPUT: STAYS AT THE BOTTOM
# ============================================================

pending_prompt = st.session_state.pop("pending_prompt", None)

prompt = st.chat_input(
    "Message your agent...",
    key="agent_chat_input",
)

if pending_prompt and not prompt:
    prompt = pending_prompt


# ============================================================
# PROCESS NEW MESSAGE
# ============================================================

if prompt and prompt.strip():
    prompt = prompt.strip()

    # Refresh references after any conversation switch.
    current_id = st.session_state.current_conversation_id
    current_conversation = st.session_state.conversations[current_id]

    current_conversation["messages"].append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    if current_conversation["title"] == "New Chat":
        current_conversation["title"] = (
            prompt.replace("\n", " ").strip()[:35]
        )

    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Working through your request..."):
            output, return_code = run_agent(
                prompt,
                current_id,
            )

            answer = extract_final_response(output)
            details = get_message_details(output, return_code)

            if return_code != 0:
                st.error(
                    "The backend reported an error. "
                    "Inspect the execution details below."
                )

            st.markdown(answer)
            render_message_details(details)

    current_conversation["messages"].append(
        {
            "role": "assistant",
            "content": answer,
            "details": details,
        }
    )

    # Keep a bounded number of messages per conversation.
    max_messages = 100
    if len(current_conversation["messages"]) > max_messages:
        current_conversation["messages"] = (
            current_conversation["messages"][-max_messages:]
        )


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div class="footer">
        Knowledge-to-Action Agent · Multi-Agent AI · RAG · Research · Tools · Memory
    </div>
    """,
    unsafe_allow_html=True,
)
