import logging
from typing import Any

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

logger = logging.getLogger("voice_ai.rag.vectorstore")


class ChromaVectorStore:
    """Wrapper for ChromaDB vector store."""

    def __init__(self, persist_dir: str, embeddings: Embeddings) -> None:
        self._persist_dir = persist_dir
        self._embeddings = embeddings
        self._client: Chroma | None = None

    def _get_client(self) -> Chroma:
        """Get or create the Chroma client."""
        if self._client is None:
            logger.info("Initializing ChromaDB at %s", self._persist_dir)
            self._client = Chroma(
                persist_directory=self._persist_dir,
                embedding_function=self._embeddings,
            )
        return self._client

    def add_documents(self, documents: list[Document]) -> int:
        """Add documents to the store. Returns count of added documents."""
        if not documents:
            logger.warning("No documents to add")
            return 0
        client = self._get_client()
        client.add_documents(documents)
        logger.info("Added %d documents to ChromaDB", len(documents))
        return len(documents)

    def as_retriever(self, k: int = 3) -> Any:
        """Get a retriever from the store."""
        client = self._get_client()
        return client.as_retriever(search_kwargs={"k": k})

    def clear(self) -> None:
        """Clear all documents from the store."""
        client = self._get_client()
        try:
            client.delete_collection()
            logger.info("Cleared ChromaDB collection")
        except Exception:
            logger.debug("No collection to clear")
        self._client = None

    def get_stats(self) -> dict[str, int | str]:
        """Get statistics about the store."""
        client = self._get_client()
        try:
            collection = client._collection
            count = collection.count()
        except Exception:
            count = 0
        return {
            "document_count": count,
            "persist_dir": self._persist_dir,
        }
