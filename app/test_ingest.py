from dotenv import load_dotenv

load_dotenv()

from app.rag.ingest import ingest_document


file_path = "data/uploads/ml_notes.txt"

chunks_count = ingest_document(
    file_path
)

print(
    f"\nTotal chunks added: {chunks_count}"
)