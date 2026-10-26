# System Architecture — Knowledge-to-Action Agent

## 1. Overview

Knowledge-to-Action Agent is a multi-agent AI application that processes user requests through specialized agents coordinated using LangGraph. Depending on the request, the system can create plans, perform web research, retrieve information from documents, and evaluate generated results.

## 2. High-Level Architecture

```text
                 +----------------------+
                 |      User Query      |
                 +----------+-----------+
                            |
                            v
                 +----------------------+
                 |     Orchestrator     |
                 |  Request Routing     |
                 +----------+-----------+
                            |
              +-------------+-------------+
              |             |             |
              v             v             v
        +-----------+ +-----------+ +-----------+
        |  Planner  | | Researcher| |    RAG    |
        |   Agent   | |   Agent   | |   Agent   |
        +-----------+ +-----------+ +-----+-----+
                                         |
                                         v
                                +------------------+
                                | Hybrid Retrieval |
                                | Vector + BM25    |
                                +--------+---------+
                                         |
                                         v
                                +------------------+
                                | FlashRank        |
                                | Reranking        |
                                +--------+---------+
                                         |
                                         v
                                +------------------+
                                | Retrieved        |
                                | Evidence         |
                                +--------+---------+
                                         |
                                         v
                 +-----------------------+ 
                 |      Critic Agent     |
                 | Result Verification   |
                 +-----------+-----------+
                             |
                    +--------+--------+
                    |                 |
                  PASS               FAIL
                    |                 |
                    v                 v
             +-------------+   +--------------+
             | Final Result|   | Retry Agent  |
             +------+------+   +------+-------+
                    |                 |
                    v                 |
             +-------------+          |
             | Memory and  |<---------+
             | Persistence |
             +------+------+
                    |
                    v
             +-------------+
             | User Output |
             +-------------+
```

*Note: This diagram represents the conceptual workflow. Exact routing and retry behavior are determined by the implemented LangGraph graph.*

## 3. Main Components

### 3.1 Orchestrator

Receives the user request and selects the appropriate processing route.

### 3.2 Planner Agent

Breaks complex tasks into practical, ordered steps. It can revise its plan based on critic feedback.

### 3.3 Research Agent

Uses the configured web research integration to collect information relevant to a query.

### 3.4 RAG Agent

Answers questions using information retrieved from uploaded PDF and TXT documents. The response is generated using the retrieved context.

### 3.5 Retrieval Pipeline

The retrieval pipeline combines keyword-based BM25 retrieval with vector similarity search. FlashRank reranks candidate passages to prioritize potentially relevant evidence.

### 3.6 Critic Agent

Evaluates the generated result. For RAG requests, it receives retrieved document evidence and checks whether factual claims are supported. The critic returns a verification status and feedback.

### 3.7 Retry Workflow

When verification fails, the graph can route the request back to an appropriate agent for revision, subject to the configured retry limit.

### 3.8 Memory and Persistence

SQLite-backed persistence supports conversation or workflow state across executions, depending on the configured session and checkpoint identifiers.

### 3.9 Execution Tracing

The tracing component records information about agent execution to help inspect behavior and diagnose failures.

### 3.10 User Interface

The command-line application and Streamlit interface provide ways to interact with the system.

## 4. RAG Processing Flow

1. The user submits a document-related question.
2. The retriever searches the indexed documents.
3. Hybrid retrieval combines keyword and semantic results.
4. Reranking prioritizes the candidate passages.
5. The RAG agent sends the question and retrieved passages to the language model.
6. The generated answer and retrieved evidence are passed to the critic.
7. The critic returns PASS or FAIL with feedback.
8. The workflow returns the final result and source information.

## 5. Data Storage

- **ChromaDB:** Stores document embeddings and associated metadata.
- **SQLite:** Supports configured persistence and execution state.
- **Upload directory:** Holds uploaded source documents.
- **Environment configuration:** Stores local API credentials and configuration values outside source code.

## 6. Reliability and Limitations

The critic and retry workflow are intended to improve answer quality, but they cannot guarantee complete factual accuracy. Retrieval quality depends on document content, chunking, metadata, search settings, and reranking. Verification results should therefore be supported by automated tests and broader evaluation.

## 7. Summary

The architecture combines multi-agent orchestration, retrieval-augmented generation, hybrid search, reranking, persistence, and critic-based verification in one application.
