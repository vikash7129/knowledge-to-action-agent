import os
import unittest
from unittest.mock import Mock, patch

from langchain_core.documents import Document

from app.rag.answer_evaluation import (
    tokenize,
    context_relevance,
    answer_relevance,
    faithfulness_indicator,
    evaluate_answer,
    evaluate_answer_with_llm,
)


class AnswerEvaluationTests(unittest.TestCase):

    def setUp(self):
        self.question = "How does reinforcement learning use rewards?"

        self.documents = [
            Document(
                page_content=(
                    "Reinforcement learning trains an agent "
                    "using rewards and penalties."
                ),
                metadata={"source": "ml_notes.txt"},
            )
        ]

    def test_tokenize_removes_common_words(self):
        tokens = tokenize("The agent learns using rewards.")
        self.assertIn("agent", tokens)
        self.assertIn("rewards", tokens)
        self.assertNotIn("the", tokens)

    def test_tokenize_handles_non_string_input(self):
        self.assertEqual(tokenize(None), [])
        self.assertEqual(tokenize(123), [])

    def test_context_relevance_with_matching_context(self):
        score = context_relevance(self.question, self.documents)
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_context_relevance_without_documents(self):
        self.assertEqual(context_relevance(self.question, []), 0.0)

    def test_context_relevance_with_empty_question(self):
        self.assertEqual(context_relevance("", self.documents), 0.0)

    def test_answer_relevance_with_matching_answer(self):
        score = answer_relevance(
            self.question,
            "Reinforcement learning uses rewards.",
        )
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_answer_relevance_with_empty_answer(self):
        self.assertEqual(answer_relevance(self.question, ""), 0.0)

    def test_faithfulness_indicator_with_matching_context(self):
        score = faithfulness_indicator(
            "Learning uses rewards and penalties.",
            self.documents,
        )
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_faithfulness_indicator_without_documents(self):
        self.assertEqual(
            faithfulness_indicator("An answer.", []),
            0.0,
        )

    def test_evaluate_answer_returns_expected_fields(self):
        result = evaluate_answer(
            self.question,
            "Reinforcement learning uses rewards.",
            self.documents,
        )
        self.assertIn("context_relevance", result)
        self.assertIn("answer_relevance", result)
        self.assertIn("faithfulness_indicator", result)
        self.assertIn("warnings", result)
        self.assertEqual(result["warnings"], [])

    def test_empty_retrieval_generates_warning(self):
        result = evaluate_answer(
            self.question,
            "I could not find relevant information.",
            [],
        )
        self.assertIn(
            "No retrieved documents are available.",
            result["warnings"],
        )

    def test_empty_answer_generates_warning(self):
        result = evaluate_answer(self.question, "", self.documents)
        self.assertIn(
            "The generated answer is empty.",
            result["warnings"],
        )

    def test_whitespace_only_answer_generates_warning(self):
        result = evaluate_answer(
            self.question,
            "   \n\t   ",
            self.documents,
        )
        self.assertIn(
            "The generated answer is empty.",
            result["warnings"],
        )

    def test_empty_document_text_generates_warning(self):
        documents = [
            Document(
                page_content="   ",
                metadata={"source": "empty.txt"},
            )
        ]
        result = evaluate_answer(
            self.question,
            "Some answer.",
            documents,
        )
        self.assertIn(
            "Retrieved documents contain no usable text.",
            result["warnings"],
        )

    def test_llm_judge_skips_when_no_documents(self):
        result = evaluate_answer_with_llm(
            self.question,
            "Some answer.",
            [],
        )
        self.assertEqual(result["judge_status"], "skipped")
        self.assertIsNone(result["judge_context_relevance"])
        self.assertIsNone(result["judge_answer_relevance"])
        self.assertIsNone(result["judge_faithfulness"])
        self.assertIn("No retrieved documents", result["judge_error"])

    def test_llm_judge_skips_when_documents_are_blank(self):
        documents = [
            Document(
                page_content="   ",
                metadata={"source": "empty.txt"},
            )
        ]
        result = evaluate_answer_with_llm(
            self.question,
            "Some answer.",
            documents,
        )
        self.assertEqual(result["judge_status"], "skipped")
        self.assertIsNone(result["judge_context_relevance"])
        self.assertIsNone(result["judge_answer_relevance"])
        self.assertIsNone(result["judge_faithfulness"])
        self.assertIn("no usable text", result["judge_error"])

    @patch("app.rag.answer_evaluation.ChatGoogleGenerativeAI")
    def test_llm_judge_accepts_valid_response(self, mock_llm_class):
        mock_llm_class.return_value.invoke.return_value = Mock(
            content=(
                '{"context_relevance": 0.9, '
                '"answer_relevance": 0.8, '
                '"faithfulness": 1.0, '
                '"reasons": {'
                '"faithfulness": "Claims are supported."'
                '}}'
            )
        )

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            result = evaluate_answer_with_llm(
                self.question,
                "Reinforcement learning uses rewards and penalties.",
                self.documents,
            )

        self.assertEqual(result["judge_status"], "success")
        self.assertEqual(result["judge_context_relevance"], 0.9)
        self.assertEqual(result["judge_answer_relevance"], 0.8)
        self.assertEqual(result["judge_faithfulness"], 1.0)
        self.assertIsNone(result["judge_error"])
        mock_llm_class.return_value.invoke.assert_called_once()

    @patch("app.rag.answer_evaluation.ChatGoogleGenerativeAI")
    def test_llm_judge_rejects_invalid_score(self, mock_llm_class):
        mock_llm_class.return_value.invoke.return_value = Mock(
            content=(
                '{"context_relevance": 2.0, '
                '"answer_relevance": 0.8, '
                '"faithfulness": 0.9, '
                '"reasons": {}}'
            )
        )

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            result = evaluate_answer_with_llm(
                self.question,
                "Some answer.",
                self.documents,
            )

        self.assertEqual(result["judge_status"], "error")
        self.assertIsNone(result["judge_context_relevance"])
        self.assertIn("Invalid judge score", result["judge_error"])

    @patch("app.rag.answer_evaluation.ChatGoogleGenerativeAI")
    def test_llm_judge_handles_model_exception(self, mock_llm_class):
        mock_llm_class.return_value.invoke.side_effect = RuntimeError(
            "Simulated test failure"
        )

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            result = evaluate_answer_with_llm(
                self.question,
                "Some answer.",
                self.documents,
            )

        self.assertEqual(result["judge_status"], "error")
        self.assertIsNone(result["judge_faithfulness"])
        self.assertIn("RuntimeError", result["judge_error"])
        self.assertIn("Simulated test failure", result["judge_error"])

    def test_llm_judge_handles_missing_api_key(self):
        with patch.dict(
            os.environ,
            {"GOOGLE_API_KEY": "", "GEMINI_API_KEY": ""},
        ):
            with patch(
                "app.rag.answer_evaluation.ChatGoogleGenerativeAI"
            ) as mock_llm_class:
                result = evaluate_answer_with_llm(
                    self.question,
                    "Some answer.",
                    self.documents,
                )

        self.assertEqual(result["judge_status"], "error")
        self.assertIn("API key not found", result["judge_error"])
        mock_llm_class.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)