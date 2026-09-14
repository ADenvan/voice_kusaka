import os
from typing import Any

import faiss
from langchain_community.docstore import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from loguru import logger


class FaissVectorStore:
    """Wrapper for FAISS vector store."""

    _INDEX_FILE = "index.faiss"
    _PKL_FILE = "index.pkl"

    def __init__(self, index_dir: str, embeddings: Embeddings) -> None:
        self._index_dir = index_dir
        self._embeddings = embeddings
        self._index: FAISS | None = None

    def _index_path(self) -> str:
        return os.path.join(self._index_dir, self._INDEX_FILE)

    def _pkl_path(self) -> str:
        return os.path.join(self._index_dir, self._PKL_FILE)

    def is_index_present(self) -> bool:
        """Check whether a saved FAISS index exists."""
        return os.path.exists(self._index_path()) and os.path.exists(self._pkl_path())

    def _create_empty_index(self) -> FAISS:
        """Create a truly empty FAISS index with correct embedding dimension."""
        logger.info("Creating empty FAISS index at {}", self._index_dir)
        os.makedirs(self._index_dir, exist_ok=True)
        reference_vector = self._embeddings.embed_query("")
        dimension = len(reference_vector)
        flat_index = faiss.IndexFlatL2(dimension)
        self._index = FAISS(
            embedding_function=self._embeddings,
            index=flat_index,
            docstore=InMemoryDocstore(),
            index_to_docstore_id={},
        )
        self._save_index()
        return self._index

    def _load_index(self) -> FAISS:
        """Load an existing FAISS index or create an empty one."""
        if self._index is None:
            if self.is_index_present():
                logger.info("Loading FAISS index from {}", self._index_dir)
                self._index = FAISS.load_local(
                    self._index_dir,
                    self._embeddings,
                    allow_dangerous_deserialization=True,
                )
            else:
                self._create_empty_index()
        assert self._index is not None
        return self._index

    def _save_index(self) -> None:
        """Persist the current FAISS index to disk."""
        if self._index is not None:
            os.makedirs(self._index_dir, exist_ok=True)
            self._index.save_local(self._index_dir)

    def build_from_documents(self, documents: list[Document]) -> int:
        """Build a new FAISS index from documents."""
        if not documents:
            logger.warning("No documents to build FAISS index")
            return 0

        self.clear()
        os.makedirs(self._index_dir, exist_ok=True)
        logger.info("Building FAISS index from {} documents", len(documents))
        self._index = FAISS.from_documents(documents, self._embeddings)
        self._save_index()
        logger.info("FAISS index saved to {}", self._index_dir)
        return len(documents)

    def add_documents(self, documents: list[Document]) -> int:
        """Add documents to the existing index."""
        if not documents:
            logger.warning("No documents to add")
            return 0

        index = self._load_index()
        index.add_documents(documents)
        self._save_index()
        logger.info("Added {} documents to FAISS index", len(documents))
        return len(documents)

    def as_retriever(self, k: int = 3) -> Any:
        """Get a retriever from the store."""
        index = self._load_index()
        return index.as_retriever(search_kwargs={"k": k})

    def clear(self) -> None:
        """Clear all documents from the index."""
        self._index = None
        self._create_empty_index()
        logger.info("Cleared FAISS index at {}", self._index_dir)

    def get_stats(self) -> dict[str, int | str]:
        """Get statistics about the store."""
        try:
            index = self._load_index()
            count = index.index.ntotal if index.index is not None else 0
        except Exception:
            count = 0
        return {
            "document_count": count,
            "index_dir": self._index_dir,
        }

    def similarity_search(self, query: str, k: int = 3) -> list[Document]:
        """Search the index for documents similar to the query."""
        index = self._load_index()
        return index.similarity_search(query, k=k)
