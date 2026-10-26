import unittest
from unittest.mock import Mock, patch

from langchain_core.documents import Document

from app.rag.rag_chain import generate_answer


class RagChainUnitTests(unittest.TestCase):

    def setUp(self):
        self.question = "What is reinforcement learning?"

        self.documents = [
            Document(
                page_content=(
                    "Reinforcement learning trains an agent "
                    "using rewards and penalties."
                ),
                metadata={"source": "ml_notes.txt"},
            )
        ]

    @patch("app.rag.rag_chain.ChatGoogleGenerativeAI")
    def test_successful_answer_includes_source(self, mock_llm_class):
        mock_llm_class.return_value.invoke.return_value = Mock(
            content="It trains an agent using rewards and penalties."
        )

        result = generate_answer(self.question, self.documents)

        self.assertIn("rewards and penalties", result)
        self.assertIn("Sources:", result)
        self.assertIn("ml_notes.txt", result)
        mock_llm_class.return_value.invoke.assert_called_once()

    @patch("app.rag.rag_chain.ChatGoogleGenerativeAI")
    def test_empty_retrieval_skips_model(self, mock_llm_class):
        result = generate_answer(self.question, [])

        self.assertIn("could not find relevant information", result)
        self.assertIn("No relevant source found", result)
        mock_llm_class.assert_not_called()

    @patch("app.rag.rag_chain.ChatGoogleGenerativeAI")
    def test_blank_documents_skip_model(self, mock_llm_class):
        documents = [
            Document(
                page_content="   ",
                metadata={"source": "empty.txt"},
            )
        ]

        result = generate_answer(self.question, documents)

        self.assertIn("no usable text", result)
        self.assertIn("empty.txt", result)
        mock_llm_class.assert_not_called()

    @patch("app.rag.rag_chain.ChatGoogleGenerativeAI")
    def test_duplicate_sources_are_listed_once(self, mock_llm_class):
        mock_llm_class.return_value.invoke.return_value = Mock(
            content="The agent learns using rewards."
        )

        documents = [
            Document(
                page_content="Agents learn using rewards.",
                metadata={"source": "ml_notes.txt"},
            ),
            Document(
                page_content="Rewards guide learning.",
                metadata={"source": "ml_notes.txt"},
            ),
        ]

        result = generate_answer(self.question, documents)

        self.assertEqual(result.count("- ml_notes.txt"), 1)

    @patch("app.rag.rag_chain.ChatGoogleGenerativeAI")
    def test_model_exception_returns_safe_message(self, mock_llm_class):
        mock_llm_class.return_value.invoke.side_effect = RuntimeError(
            "Simulated failure"
        )

        result = generate_answer(self.question, self.documents)

        self.assertIn("language model request failed", result)
        self.assertIn("ml_notes.txt", result)
        self.assertNotIn("Simulated failure", result)

    @patch("app.rag.rag_chain.ChatGoogleGenerativeAI")
    def test_empty_model_response_returns_fallback(self, mock_llm_class):
        mock_llm_class.return_value.invoke.return_value = Mock(
            content="   "
        )

        result = generate_answer(self.question, self.documents)

        self.assertIn("empty answer", result)
        self.assertIn("ml_notes.txt", result)

    @patch("app.rag.rag_chain.ChatGoogleGenerativeAI")
    def test_missing_source_metadata_is_handled(self, mock_llm_class):
        mock_llm_class.return_value.invoke.return_value = Mock(
            content="The available text describes reinforcement learning."
        )

        documents = [
            Document(page_content="Reinforcement learning uses rewards.")
        ]

        result = generate_answer(self.question, documents)

        self.assertIn("Source metadata unavailable", result)

    @patch("app.rag.rag_chain.ChatGoogleGenerativeAI")
    def test_conversation_history_is_passed_to_prompt(
        self,
        mock_llm_class,
    ):
        mock_llm_class.return_value.invoke.return_value = Mock(
            content="It learns from rewards."
        )

        history = [
            "Previous question: Explain reinforcement learning.",
            "Previous answer: It uses rewards.",
        ]

        generate_answer(
            "Give an example of it.",
            self.documents,
            conversation_history=history,
        )

        prompt = mock_llm_class.return_value.invoke.call_args.args[0]

        self.assertIn("Give an example of it.", prompt)
        self.assertIn("Previous question", prompt)
        self.assertIn("Conversation history is not factual evidence", prompt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
