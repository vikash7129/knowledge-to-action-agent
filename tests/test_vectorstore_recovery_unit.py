
import unittest
from unittest.mock import patch

from langchain_core.documents import Document

from app.rag import vectorstore as target


class FakeEmbeddings:
    """Fake embeddings: no external API calls."""

    def embed_documents(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeCollection:
    """In-memory replacement for Chroma's collection API."""

    def __init__(self, store):
        self.store = store

    def add(self, ids, documents, metadatas, embeddings):
        for record_id in ids:
            if record_id in self.store.records:
                raise ValueError(f"Duplicate ID: {record_id}")

        if not (
            len(ids) == len(documents)
            == len(metadatas) == len(embeddings)
        ):
            raise ValueError("Record lengths do not match.")

        for record_id, document, metadata, embedding in zip(
            ids, documents, metadatas, embeddings
        ):
            self.store.records[record_id] = {
                "document": document,
                "metadata": dict(metadata),
                "embedding": list(embedding),
            }


class FakeVectorstore:
    """A tiny in-memory database used only by these tests."""

    def __init__(self):
        self.records = {
            "old-1": {
                "document": "Original indexed content",
                "metadata": {
                    "source": "ml_notes.txt",
                    "filename": "ml_notes.txt",
                    "file_type": "txt",
                    "document_id": "old-document",
                    "chunk_id": 0,
                },
                "embedding": [0.4, 0.5, 0.6],
            }
        }

        self._collection = FakeCollection(self)
        self.fail_next_id_lookup = False

    def get(self, ids=None, where=None, include=None):
        if ids is not None and self.fail_next_id_lookup:
            self.fail_next_id_lookup = False
            raise RuntimeError("Simulated verification failure")

        if ids is not None:
            selected_ids = [
                record_id for record_id in ids
                if record_id in self.records
            ]
        elif where:
            source = where.get("source")
            selected_ids = [
                record_id
                for record_id, record in self.records.items()
                if record["metadata"].get("source") == source
            ]
        else:
            selected_ids = list(self.records)

        result = {"ids": selected_ids}

        if include is None:
            include = []

        if "documents" in include:
            result["documents"] = [
                self.records[key]["document"]
                for key in selected_ids
            ]

        if "metadatas" in include:
            result["metadatas"] = [
                dict(self.records[key]["metadata"])
                for key in selected_ids
            ]

        if "embeddings" in include:
            result["embeddings"] = [
                list(self.records[key]["embedding"])
                for key in selected_ids
            ]

        return result

    def delete(self, ids):
        for record_id in ids:
            self.records.pop(record_id, None)


def make_chunk(content="Updated indexed content"):
    return Document(
        page_content=content,
        metadata={
            "source": "ml_notes.txt",
            "filename": "ml_notes.txt",
            "file_type": "txt",
            "document_id": "new-document",
            "page": None,
            "chunk_id": 0,
        },
    )


class VectorstoreRecoveryTests(unittest.TestCase):

    def setUp(self):
        self.store = FakeVectorstore()
        self.embedding_model = FakeEmbeddings()

    def run_with_mocks(self, chunks):
        embeddings_patch = patch.object(
            target, "get_embeddings",
            return_value=self.embedding_model,
        )
        store_patch = patch.object(
            target, "Chroma",
            return_value=self.store,
        )

        return embeddings_patch, store_patch

    def test_successful_replacement(self):
        embeddings_patch, store_patch = self.run_with_mocks(
            [make_chunk()]
        )

        with embeddings_patch, store_patch:
            result = target.create_vectorstore([make_chunk()])

        self.assertIs(result, self.store)
        self.assertNotIn("old-1", self.store.records)

        remaining = list(self.store.records.values())
        self.assertEqual(len(remaining), 1)
        self.assertEqual(
            remaining[0]["document"],
            "Updated indexed content",
        )

    def test_failed_verification_restores_old_records(self):
        self.store.fail_next_id_lookup = True

        embeddings_patch, store_patch = self.run_with_mocks(
            [make_chunk()]
        )

        with embeddings_patch, store_patch:
            with self.assertRaisesRegex(
                RuntimeError, "Simulated verification failure"
            ):
                target.create_vectorstore([make_chunk()])

        self.assertIn("old-1", self.store.records)
        self.assertEqual(
            self.store.records["old-1"]["document"],
            "Original indexed content",
        )

        self.assertEqual(
            list(self.store.records.keys()),
            ["old-1"],
        )

    def test_embedding_failure_does_not_open_database(self):
        class BrokenEmbeddings:
            def embed_documents(self, texts):
                raise RuntimeError("Simulated embedding failure")

        with (
            patch.object(
                target, "get_embeddings",
                return_value=BrokenEmbeddings(),
            ),
            patch.object(target, "Chroma") as chroma_constructor,
        ):
            with self.assertRaisesRegex(
                RuntimeError, "Simulated embedding failure"
            ):
                target.create_vectorstore([make_chunk()])

            chroma_constructor.assert_not_called()

        self.assertEqual(
            list(self.store.records.keys()),
            ["old-1"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
