
from typing import List
from uuid import uuid4

from langchain_core.documents import Document
from langchain_chroma import Chroma

from .embeddings import get_embeddings


CHROMA_PATH = "data/chroma_db"

REQUIRED_METADATA = [
    "source",
    "filename",
    "file_type",
    "document_id",
    "page",
    "chunk_id",
]


def validate_chunks(chunks: List[Document]) -> tuple[str, str]:
    """Validate all chunks before modifying the database."""

    if not chunks:
        raise ValueError("No chunks supplied.")

    for index, chunk in enumerate(chunks):
        if not isinstance(chunk, Document):
            raise TypeError(f"Item {index} is not a Document.")

        if not chunk.page_content or not chunk.page_content.strip():
            raise ValueError(f"Chunk {index} has empty content.")

        metadata = chunk.metadata or {}
        missing = [
            key for key in REQUIRED_METADATA if key not in metadata
        ]

        if missing:
            raise ValueError(
                f"Chunk {index} is missing metadata: {missing}"
            )

        if not metadata.get("source"):
            raise ValueError(f"Chunk {index} has no source.")

        if not metadata.get("document_id"):
            raise ValueError(f"Chunk {index} has no document_id.")

        if not isinstance(metadata["chunk_id"], int):
            raise ValueError(
                f"Chunk {index} must have an integer chunk_id."
            )

    sources = {str(c.metadata["source"]) for c in chunks}
    document_ids = {str(c.metadata["document_id"]) for c in chunks}

    if len(sources) != 1:
        raise ValueError("A batch must contain only one source.")

    if len(document_ids) != 1:
        raise ValueError("A batch must contain only one document_id.")

    return next(iter(sources)), next(iter(document_ids))


def clean_metadata(metadata: dict) -> dict:
    """Chroma metadata cannot contain None values."""

    return {
        key: value
        for key, value in metadata.items()
        if value is not None
    }


def as_embedding_lists(embeddings) -> list[list[float]]:
    """Convert returned embedding arrays into lists of floats."""

    if hasattr(embeddings, "tolist"):
        embeddings = embeddings.tolist()

    return [
        [float(value) for value in embedding]
        for embedding in embeddings
    ]


def read_source(vectorstore: Chroma, source_name: str) -> dict:
    """Read a source snapshot, including stored embeddings."""

    return vectorstore.get(
        where={"source": source_name},
        include=["documents", "metadatas", "embeddings"],
    )


def restore_snapshot(
    vectorstore: Chroma,
    snapshot: dict,
    source_name: str,
) -> None:
    """Restore missing old records without duplicating existing IDs."""

    old_ids = snapshot.get("ids", []) or []

    if not old_ids:
        return

    old_documents = snapshot.get("documents", []) or []
    old_metadatas = snapshot.get("metadatas", []) or []
    old_embeddings = snapshot.get("embeddings")

    if old_embeddings is None:
        raise RuntimeError("Rollback failed: old embeddings unavailable.")

    old_embeddings = as_embedding_lists(old_embeddings)

    if not (
        len(old_ids)
        == len(old_documents)
        == len(old_metadatas)
        == len(old_embeddings)
    ):
        raise RuntimeError("Rollback failed: incomplete old snapshot.")

    current = read_source(vectorstore, source_name)
    current_ids = set(current.get("ids", []) or [])
    missing_indices = [
        index for index, old_id in enumerate(old_ids)
        if old_id not in current_ids
    ]

    # Chroma's collection API accepts precomputed embeddings directly.
    if missing_indices:
        vectorstore._collection.add(
            ids=[old_ids[i] for i in missing_indices],
            documents=[old_documents[i] for i in missing_indices],
            metadatas=[old_metadatas[i] for i in missing_indices],
            embeddings=[old_embeddings[i] for i in missing_indices],
        )

    restored = read_source(vectorstore, source_name)
    restored_ids = set(restored.get("ids", []) or [])

    if not set(old_ids).issubset(restored_ids):
        raise RuntimeError("Rollback verification failed for old records.")


def create_vectorstore(chunks: List[Document]) -> Chroma:
    """
    Replace one source safely.

    Generate embeddings first, add and verify new records, then delete
    old records. On failure, attempt to restore the old source snapshot.
    """

    source_name, document_id = validate_chunks(chunks)

    texts = [chunk.page_content.strip() for chunk in chunks]
    metadatas = [clean_metadata(chunk.metadata) for chunk in chunks]
    new_ids = [str(uuid4()) for _ in chunks]

    embeddings_model = get_embeddings()

    print(f"Generating embeddings before database changes: {source_name}")

    # An embedding failure here leaves existing Chroma records untouched.
    new_embeddings = embeddings_model.embed_documents(texts)

    if len(new_embeddings) != len(chunks):
        raise RuntimeError(
            "Embedding count mismatch. Existing records were not changed."
        )

    vectorstore = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings_model,
    )

    snapshot = read_source(vectorstore, source_name)
    old_ids = snapshot.get("ids", []) or []

    print(f"Existing chunks for {source_name}: {len(old_ids)}")
    print("Recovery snapshot prepared.")
    print("Adding new chunks without deleting the old ones...")

    try:
        # Use the supported Chroma collection API with precomputed vectors.
        vectorstore._collection.add(
            ids=new_ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=as_embedding_lists(new_embeddings),
        )

        new_records = vectorstore.get(
            ids=new_ids,
            include=["documents", "metadatas"],
        )

        if set(new_records.get("ids", []) or []) != set(new_ids):
            raise RuntimeError("New chunk ID verification failed.")

        stored_documents = new_records.get("documents", []) or []
        stored_metadatas = new_records.get("metadatas", []) or []

        if len(stored_documents) != len(chunks):
            raise RuntimeError("New document count verification failed.")

        if stored_documents != texts:
            raise RuntimeError("Stored content does not match new content.")

        for metadata in stored_metadatas:
            if (
                metadata.get("source") != source_name
                or str(metadata.get("document_id")) != document_id
            ):
                raise RuntimeError("New metadata verification failed.")

        print("New chunk verification: PASS")

        # Old IDs are removed only after the new batch is verified.
        if old_ids:
            vectorstore.delete(ids=old_ids)

        final_records = read_source(vectorstore, source_name)
        final_ids = set(final_records.get("ids", []) or [])

        if final_ids != set(new_ids):
            raise RuntimeError("Final source replacement verification failed.")

        print(f"Old chunks safely replaced: {source_name}")
        print(f"New chunks stored: {len(chunks)}")
        print(f"Document ID: {document_id}")
        print("Metadata validation: PASS")
        print("Final count verification: PASS")

        return vectorstore

    except Exception as original_error:
        print("ERROR: Replacement failed. Attempting rollback...")

        rollback_errors = []

        # Restore old records first, including any records deleted before
        # an error occurred. Keep new records until old records are verified.
        try:
            restore_snapshot(vectorstore, snapshot, source_name)
        except Exception as restore_error:
            rollback_errors.append(
                f"Old-record restoration failed: {restore_error}"
            )

        if not rollback_errors:
            try:
                vectorstore.delete(ids=new_ids)

                final_records = read_source(vectorstore, source_name)
                final_ids = set(final_records.get("ids", []) or [])

                if final_ids != set(old_ids):
                    raise RuntimeError(
                        "Final rollback IDs do not match the old snapshot."
                    )

                print("Rollback verification: PASS")
                print("Previous source records have been restored.")

            except Exception as cleanup_error:
                rollback_errors.append(
                    f"New-record cleanup or rollback verification failed: "
                    f"{cleanup_error}"
                )

        if rollback_errors:
            raise RuntimeError(
                f"Ingestion failed: {original_error}. "
                f"Recovery also reported: {' | '.join(rollback_errors)}. "
                "Stop ingestion and preserve the database backup."
            ) from original_error

        raise
