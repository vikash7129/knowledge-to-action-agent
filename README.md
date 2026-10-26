# Knowledge-to-Action Agent

An AI-powered multi-agent system that converts user queries into actionable results using planning, web research, document-based Retrieval-Augmented Generation (RAG), tool execution, memory, and critic-based verification.

## 1. Project Overview

Knowledge-to-Action Agent is a multi-agent AI application built to answer questions, develop practical plans, research information, and retrieve relevant knowledge from uploaded documents.

The system uses LangGraph to coordinate agent workflows and a critic agent to evaluate generated responses before presenting the final result.

## 2. Key Features

- **Multi-Agent Architecture:** Coordinates specialized agents through a LangGraph workflow.
- **Intelligent Routing:** Selects an appropriate workflow for the user's request.
- **Planning Agent:** Converts complex requests into actionable steps.
- **Research Agent:** Supports web research using Tavily.
- **RAG Pipeline:** Answers questions using uploaded PDF and TXT documents.
- **Hybrid Retrieval:** Combines vector retrieval and BM25-based keyword retrieval.
- **Reranking:** Uses FlashRank to improve the ordering of retrieved document passages.
- **Vector Database:** Stores document embeddings in ChromaDB.
- **Conversational Memory:** Maintains conversation history and uses SQLite-backed persistence.
- **Critic-Based Verification:** Evaluates answer relevance and whether document-based claims are supported by retrieved evidence.
- **Retry Workflow:** Allows selected agents to revise their results when verification fails, subject to the configured retry limit.
- **Execution Tracing:** Records agent execution information for debugging and inspection.
- **Streamlit Interface:** Provides a user interface for interacting with the application.
- **Evaluation Utilities:** Supports retrieval and answer-quality evaluation.

## 3. System Architecture

The application follows this general workflow:

1. The user submits a request through the application interface.
2. The orchestrator determines the appropriate processing route.
3. The selected agent processes the request.
4. The RAG workflow retrieves relevant documents when document-based knowledge is required.
5. The critic evaluates the generated result.
6. If verification fails, the workflow may retry within the configured limit.
7. The system returns the final response and relevant source information.
8. Conversation and execution information can be persisted for later use and debugging.

## 4. Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python |
| Agent Workflow | LangGraph |
| LLM Integration | LangChain |
| Language Model | Google Gemini |
| Embeddings | Google Gemini Embeddings |
| Vector Database | ChromaDB |
| Hybrid Retrieval | BM25 and vector search |
| Reranking | FlashRank |
| Web Research | Tavily |
| Persistent Storage | SQLite |
| User Interface | Streamlit |
| Document Processing | PDF and TXT loaders |

## 5. Project Structure

```text
knowledge-to-action-agent/
├── app/
│   ├── agents/
│   │   ├── critic.py
│   │   ├── planner.py
│   │   ├── rag_agent.py
│   │   ├── state.py
│   │   └── tracing.py
│   ├── rag/
│   │   ├── retriever.py
│   │   ├── rag_chain.py
│   │   └── answer_evaluation.py
│   ├── tools/
│   ├── memory/
│   ├── api/
│   ├── main.py
│   └── streamlit_app.py
├── data/
│   ├── uploads/
│   └── chroma_db/
├── tests/
├── .env
├── requirements.txt
└── README.md
```

*Note: The structure above highlights major components. Your actual folders and filenames may differ.*

## 6. Installation and Setup

### Prerequisites

- Python 3.10 or a compatible version supported by the installed dependencies.
- Google Gemini API key.
- Tavily API key for web research features.

### Clone the Repository

```bash
git clone <your-github-repository-url>
cd knowledge-to-action-agent
```

### Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment Variables

Create a `.env` file in the project root and add the API keys required by your configuration:

```env
GOOGLE_API_KEY=your_google_api_key
TAVILY_API_KEY=your_tavily_api_key
```

Use the exact variable names expected by your code. Keep `.env` private and never commit API keys to GitHub.

## 7. Running the Application

Run the command-line agent:

```bash
python -m app.main
```

Run the Streamlit interface:

```bash
streamlit run app/streamlit_app.py
```

Use the interface or command-line application to submit a question or task.

## 8. Example Use Cases

- Explain a machine-learning concept using uploaded study notes.
- Compare information across multiple documents.
- Generate a structured implementation plan for an AI project.
- Research a topic using the configured web research tool.
- Retrieve relevant passages from PDF and TXT files.
- Verify whether a generated document-based answer is supported by retrieved evidence.

## 9. Testing and Evaluation

The project includes utilities for checking retrieval quality and evaluating generated answers.

Previously recorded results on a small retrieval evaluation dataset:

| Metric | Recorded Result |
|---|---:|
| Precision@3 | 1.00 |
| Recall@3 | 1.00 |
| MRR | 1.00 |

These results apply only to the small dataset used during evaluation and do not establish equivalent performance on unseen documents or real-world queries.

A sample machine-learning question also completed the RAG workflow with a `STATUS: PASS` critic result. This confirms that the tested request passed verification; it does not guarantee that every answer will be correct.

Run tests using the commands configured in your repository. For example, if the test file exists:

```bash
python -m pytest
```

## 10. Limitations

- Answer quality depends on the quality and coverage of uploaded documents.
- Retrieval and reranking may return irrelevant or redundant passages.
- LLM-based verification is not a guarantee of factual correctness.
- Source attribution should be checked to ensure every displayed source genuinely supports the answer.
- External research requires working API access and may be affected by service limits.
- Evaluation results from a small dataset may not generalize to other tasks.
- The application is a project prototype and should be tested further before production deployment.

## 11. Future Improvements

- Expand the evaluation dataset and add regression tests.
- Improve source-level attribution and evidence-grounded citations.
- Add authentication and access control where required.
- Improve error handling, logging, and monitoring.
- Add deployment configuration and automated integration testing.
- Evaluate retrieval and answer quality on diverse documents and queries.

## 12. Project Goal

The goal of Knowledge-to-Action Agent is to demonstrate how multiple AI agents, document retrieval, external research, persistent memory, and verification can work together in a unified application.

The project is intended for learning, experimentation, and portfolio demonstration.
