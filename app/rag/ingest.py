
from pathlib import Path

from .loader import load_document
from .splitter import split_documents
from .vectorstore import create_vectorstore


def ingest_document(file_path: str) -> int:
    """
    Load, validate, split, and safely index a PDF or TXT document.
    Returns the number of successfully indexed chunks.
    """

    path = Path(file_path).expanduser()

    print(f"\nLoading document: {path}")

    if not path.exists():
        raise FileNotFoundError(f"Document not found: {path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    documents = load_document(str(path))

    if not documents:
        raise ValueError(
            "The loader returned no usable documents. "
            "Existing indexed data has not been changed."
        )

    print(f"Documents loaded: {len(documents)}")

    for document in documents:
        metadata = document.metadata

        metadata["source"] = path.name
        metadata["filename"] = path.name
        metadata["file_type"] = path.suffix.lower().lstrip(".")

        if not metadata.get("document_id"):
            raise ValueError(
                "Missing document_id from loader. "
                "Existing indexed data has not been changed."
            )

        if "page" not in metadata:
            metadata["page"] = None

    chunks = split_documents(documents)

    if not chunks:
        raise ValueError(
            "No chunks were created. "
            "Existing indexed data has not been changed."
        )

    print(f"Chunks created: {len(chunks)}")

    for index, chunk in enumerate(chunks):
        metadata = chunk.metadata

        metadata["source"] = path.name
        metadata["filename"] = path.name
        metadata["file_type"] = path.suffix.lower().lstrip(".")
        metadata["chunk_id"] = index

        if not metadata.get("document_id"):
            raise ValueError(
                f"Chunk {index} has no document_id. "
                "Existing indexed data has not been changed."
            )

        if "page" not in metadata:
            metadata["page"] = None

    # The vectorstore function handles safe replacement and rollback.
    create_vectorstore(chunks)

    print(f"Document successfully indexed: {path.name}")
    print(f"Total chunks submitted: {len(chunks)}")

    return len(chunks)
