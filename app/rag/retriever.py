from functools import lru_cache
from typing import Optional

from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_community.document_compressors import FlashrankRerank
from langchain_core.documents import Document

from .embeddings import get_embeddings


CHROMA_PATH = "data/chroma_db"

TOP_K = 3
BM25_K = 3

# Semantic retrieval threshold
SCORE_THRESHOLD = 0.55

# Hybrid ranking constant
RRF_CONSTANT = 60

# FlashRank relevance threshold
RERANK_SCORE_THRESHOLD = 0.30


@lru_cache(maxsize=1)
def get_reranker():
    """Create and reuse the FlashRank reranker."""
    return FlashrankRerank(
        top_n=TOP_K,
        model="ms-marco-MiniLM-L-12-v2",
    )


def detect_source_from_query(query, vectorstore):
    """Detect a filename explicitly mentioned in the query."""
    if not query:
        return None

    data = vectorstore.get(include=["metadatas"])
    sources = set()

    for metadata in data.get("metadatas", []):
        if metadata:
            source = metadata.get("source")
            if source:
                sources.add(str(source))

    query_lower = query.lower()

    for source in sorted(sources, key=len, reverse=True):
        if source.lower() in query_lower:
            return source

    return None


class HybridRetriever:
    """Combine semantic search, BM25, RRF and FlashRank."""

    def __init__(
        self,
        vectorstore,
        source: Optional[str] = None,
        top_k: int = TOP_K,
    ):
        self.vectorstore = vectorstore
        self.source = source
        self.top_k = top_k

    @staticmethod
    def document_key(document):
        """Create a stable key to deduplicate retrieved chunks."""
        metadata = document.metadata or {}

        return (
            metadata.get("source", ""),
            metadata.get("chunk_id", ""),
            metadata.get("page", ""),
            document.page_content,
        )

    def invoke(self, query):
        """Retrieve, fuse, rerank, and filter relevant documents."""
        if not query or not query.strip():
            return []

        # 1. Load indexed documents for BM25 retrieval.
        stored = self.vectorstore.get(
            include=["documents", "metadatas"]
        )

        documents = []

        for content, metadata in zip(
            stored.get("documents", []),
            stored.get("metadatas", []),
        ):
            metadata = metadata or {}

            if (
                self.source
                and metadata.get("source") != self.source
            ):
                continue

            if content and content.strip():
                documents.append(
                    Document(
                        page_content=content,
                        metadata=metadata,
                    )
                )

        if not documents:
            return []

        # 2. Semantic retrieval.
        search_kwargs = {
            "k": self.top_k,
            "score_threshold": SCORE_THRESHOLD,
        }

        if self.source:
            search_kwargs["filter"] = {
                "source": self.source,
            }

        semantic_retriever = self.vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs=search_kwargs,
        )

        semantic_results = semantic_retriever.invoke(query)

        # 3. Keyword retrieval using BM25.
        keyword_retriever = BM25Retriever.from_documents(
            documents,
            k=min(BM25_K, len(documents)),
        )

        keyword_results = keyword_retriever.invoke(query)

        # 4. Combine rankings using Reciprocal Rank Fusion.
        fused_scores = {}
        documents_by_key = {}

        for results in (semantic_results, keyword_results):
            for rank, document in enumerate(results, start=1):
                key = self.document_key(document)

                fused_scores[key] = (
                    fused_scores.get(key, 0.0)
                    + 1.0 / (RRF_CONSTANT + rank)
                )

                documents_by_key[key] = document

        ranked_keys = sorted(
            fused_scores,
            key=lambda key: fused_scores[key],
            reverse=True,
        )

        # 5. Prepare a wider candidate set for reranking.
        candidate_count = min(
            max(self.top_k * 3, self.top_k),
            len(documents_by_key),
        )

        candidates = [
            documents_by_key[key]
            for key in ranked_keys[:candidate_count]
        ]

        if not candidates:
            return []

        # 6. Rerank candidates against the full query.
        reranked_documents = get_reranker().compress_documents(
            documents=candidates,
            query=query,
        )

        # 7. Filter by reranker relevance score.
        relevant_documents = []

        for document in reranked_documents:
            metadata = document.metadata or {}
            score = metadata.get("relevance_score")

            # Do not silently discard documents when no score exists.
            if score is None:
                relevant_documents.append(document)
                continue

            try:
                score = float(score)
            except (TypeError, ValueError):
                relevant_documents.append(document)
                continue

            if score >= RERANK_SCORE_THRESHOLD:
                relevant_documents.append(document)

        # 8. Return the highest-ranked relevant chunks.
        return relevant_documents[:self.top_k]


def get_retriever(source=None, query=None):
    """Create a hybrid retriever with optional filename filtering."""
    embeddings = get_embeddings()

    vectorstore = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings,
    )

    if source is None and query:
        source = detect_source_from_query(
            query,
            vectorstore,
        )

    return HybridRetriever(
        vectorstore=vectorstore,
        source=source,
        top_k=TOP_K,
    )
