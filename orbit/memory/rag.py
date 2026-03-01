from __future__ import annotations

from typing import Any

_client: Any = None
_collection: Any = None


def _ensure_initialized() -> None:
    """Lazy-initialize ChromaDB."""
    global _client, _collection  # noqa: PLW0603
    if _collection is not None:
        return

    try:
        import chromadb
    except ImportError as e:
        raise ImportError("ChromaDB required for RAG: pip install chromadb") from e

    from orbit.config import get_config

    persist_dir = str(get_config().data_dir / "chromadb")
    _client = chromadb.PersistentClient(path=persist_dir)
    _collection = _client.get_or_create_collection(name="orbit_memory", metadata={"hnsw:space": "cosine"})


def add_document(doc_id: str, content: str, metadata: dict[str, Any] | None = None) -> None:
    """Add a document to the vector store."""
    _ensure_initialized()
    assert _collection is not None
    _collection.upsert(ids=[doc_id], documents=[content], metadatas=[metadata or {}])


def search(query: str, n_results: int = 5) -> list[dict[str, Any]]:
    """Search for similar documents."""
    _ensure_initialized()
    assert _collection is not None
    results = _collection.query(query_texts=[query], n_results=n_results)
    output = []
    for i, doc_id in enumerate(results["ids"][0]):
        output.append(
            {
                "id": doc_id,
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else None,
            }
        )
    return output


def is_available() -> bool:
    """Check if ChromaDB is available."""
    try:
        import chromadb  # noqa: F401

        return True
    except ImportError:
        return False
