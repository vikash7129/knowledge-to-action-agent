
import unittest
from unittest.mock import patch

from app.rag.evaluation import (
    evaluate_query,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from app.rag.retriever import get_retriever


class RetrievalMetricTests(unittest.TestCase):

    def test_precision_at_k(self):
        retrieved = [
            "ml_notes.txt",
            "ai_notes.txt",
            "dl_notes.txt",
        ]
        relevant = {"ml_notes.txt", "dl_notes.txt"}

        self.assertAlmostEqual(
            precision_at_k(retrieved, relevant, k=3),
            2 / 3,
        )

    def test_recall_at_k(self):
        retrieved = ["ml_notes.txt", "ai_notes.txt"]
        relevant = {"ml_notes.txt", "dl_notes.txt"}

        self.assertAlmostEqual(
            recall_at_k(retrieved, relevant, k=2),
            1 / 2,
        )

    def test_reciprocal_rank(self):
        retrieved = [
            "ai_notes.txt",
            "ml_notes.txt",
            "dl_notes.txt",
        ]

        self.assertAlmostEqual(
            reciprocal_rank(retrieved, {"ml_notes.txt"}),
            1 / 2,
        )

    def test_no_relevant_result(self):
        retrieved = ["ai_notes.txt", "dl_notes.txt"]
        relevant = {"ml_notes.txt"}

        self.assertEqual(
            reciprocal_rank(retrieved, relevant),
            0.0,
        )

    def test_empty_results(self):
        self.assertEqual(
            precision_at_k([], {"ml_notes.txt"}, k=3),
            0.0,
        )
        self.assertEqual(
            recall_at_k([], {"ml_notes.txt"}, k=3),
            0.0,
        )
        self.assertEqual(
            reciprocal_rank([], {"ml_notes.txt"}),
            0.0,
        )

    def test_empty_relevant_sources(self):
        self.assertEqual(
            recall_at_k(["ml_notes.txt"], set(), k=3),
            0.0,
        )

    def test_invalid_k(self):
        with self.assertRaises(ValueError):
            precision_at_k([], {"ml_notes.txt"}, k=0)

        with self.assertRaises(ValueError):
            recall_at_k([], {"ml_notes.txt"}, k=0)


class EvaluationValidationTests(unittest.TestCase):

    @patch("app.rag.evaluation.get_retriever")
    def test_empty_retrieval_fails(self, mock_get_retriever):
        mock_get_retriever.return_value.invoke.return_value = []

        result = evaluate_query(
            "Test query",
            {"ml_notes.txt"},
        )

        self.assertFalse(result["passed"])
        self.assertIn("No documents retrieved", result["errors"])
        self.assertEqual(result["precision_at_k"], 0.0)
        self.assertEqual(result["recall_at_k"], 0.0)

    @patch("app.rag.evaluation.get_retriever")
    def test_missing_source_metadata_fails(self, mock_get_retriever):
        mock_document = type(
            "MockDocument",
            (),
            {
                "metadata": {},
                "page_content": "Test content",
            },
        )()

        mock_get_retriever.return_value.invoke.return_value = [
            mock_document
        ]

        result = evaluate_query(
            "Test query",
            {"ml_notes.txt"},
        )

        self.assertFalse(result["passed"])
        self.assertEqual(result["missing_metadata_count"], 1)

    @patch("app.rag.evaluation.get_retriever")
    def test_missing_relevant_source_fails(self, mock_get_retriever):
        mock_document = type(
            "MockDocument",
            (),
            {
                "metadata": {"source": "ai_notes.txt"},
                "page_content": "Artificial intelligence",
            },
        )()

        mock_get_retriever.return_value.invoke.return_value = [
            mock_document
        ]

        result = evaluate_query(
            "Test query",
            {"ml_notes.txt"},
        )

        self.assertFalse(result["passed"])
        self.assertIn(
            "ml_notes.txt",
            result["errors"][0],
        )


class HybridRetrieverIntegrationTests(unittest.TestCase):

    def test_explicit_source_filter(self):
        retriever = get_retriever(
            query="Explain reinforcement learning using ml_notes.txt"
        )

        documents = retriever.invoke(
            "Explain reinforcement learning"
        )

        self.assertTrue(
            documents,
            "Expected at least one result from ml_notes.txt",
        )

        self.assertTrue(
            all(
                document.metadata.get("source") == "ml_notes.txt"
                for document in documents
            ),
            "Source filtering returned a different file",
        )

    def test_cross_document_retrieval(self):
        query = (
            "Compare machine learning, deep learning, "
            "and artificial intelligence"
        )

        retriever = get_retriever(query=query)
        documents = retriever.invoke(query)

        self.assertTrue(
            documents,
            "Expected results for the cross-document query",
        )

        allowed_sources = {
            "ai_notes.txt",
            "dl_notes.txt",
            "ml_notes.txt",
        }

        returned_sources = {
            document.metadata.get("source")
            for document in documents
        }

        self.assertTrue(
            returned_sources & allowed_sources,
            "No expected source was retrieved",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
