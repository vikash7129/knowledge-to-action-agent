from pathlib import Path
from typing import List
import hashlib

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
)
from langchain_core.documents import Document


SUPPORTED_EXTENSIONS = {".pdf", ".txt"}


def create_document_id(file_path: Path) -> str:
    """
    Create a stable document ID from the normalized file path.
    This identifies the source file, not an individual chunk.
    """
    normalized_path = str(file_path.resolve()).lower()

    return hashlib.sha256(
        normalized_path.encode("utf-8")
    ).hexdigest()[:16]


def load_document(file_path: str) -> List[Document]:
    """
    Load a PDF or TXT document and normalize its metadata.

    PDF page numbers are preserved from PyPDFLoader.
    TXT documents use page=None.
    Empty pages or documents are skipped.
    """

    path = Path(file_path).expanduser()

    if not path.exists():
        raise FileNotFoundError(
            f"Document not found: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Expected a file, but received: {path}"
        )

    extension = path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))

        raise ValueError(
            f"Unsupported file type '{extension}'. "
            f"Supported formats: {supported}"
        )

    if path.stat().st_size == 0:
        raise ValueError(
            f"Document is empty: {path.name}"
        )

    if extension == ".pdf":
        loader = PyPDFLoader(str(path))

    else:
        loader = TextLoader(
            str(path),
            encoding="utf-8",
            autodetect_encoding=False,
        )

    try:
        loaded_documents = loader.load()

    except Exception as exc:
        raise RuntimeError(
            f"Failed to load '{path.name}': {exc}"
        ) from exc

    if not loaded_documents:
        raise ValueError(
            f"No pages or content could be loaded from '{path.name}'."
        )

    document_id = create_document_id(path)
    normalized_documents = []

    for index, document in enumerate(loaded_documents):
        content = document.page_content or ""

        # Skip pages/documents containing no meaningful text.
        if not content.strip():
            continue

        metadata = dict(document.metadata or {})

        # Normalize source identity consistently.
        metadata["source"] = path.name
        metadata["filename"] = path.name
        metadata["file_type"] = extension.lstrip(".")
        metadata["document_id"] = document_id

        # Preserve the PDF page number provided by the loader.
        # For TXT files, page is not applicable.
        if extension == ".pdf":
            metadata["page"] = metadata.get("page", index)
        else:
            metadata["page"] = None

        normalized_documents.append(
            Document(
                page_content=content.strip(),
                metadata=metadata,
            )
        )

    if not normalized_documents:
        raise ValueError(
            f"No readable text found in '{path.name}'. "
            "The file may be empty, scanned, or image-only."
        )

    return normalized_documents