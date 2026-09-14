from pathlib import Path

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings


class FakeEmbeddings(Embeddings):
    """Fake embeddings for testing."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


def test_vectorstore_add_documents(tmp_path: Path) -> None:
    embeddings = FakeEmbeddings()
    from src.rag.vectorstore import FaissVectorStore

    store = FaissVectorStore(str(tmp_path / "faiss"), embeddings)

    docs = [
        Document(page_content="test document 1"),
        Document(page_content="test document 2"),
    ]
    count = store.add_documents(docs)
    assert count == 2


def test_vectorstore_get_stats(tmp_path: Path) -> None:
    from src.rag.vectorstore import FaissVectorStore

    embeddings = FakeEmbeddings()
    store = FaissVectorStore(str(tmp_path / "faiss"), embeddings)

    stats = store.get_stats()
    assert "document_count" in stats
    assert "index_dir" in stats


def test_vectorstore_clear(tmp_path: Path) -> None:
    from src.rag.vectorstore import FaissVectorStore

    embeddings = FakeEmbeddings()
    store = FaissVectorStore(str(tmp_path / "faiss"), embeddings)

    docs = [Document(page_content="test")]
    store.add_documents(docs)
    store.clear()

    stats = store.get_stats()
    assert stats["document_count"] == 0


def test_vectorstore_as_retriever(tmp_path: Path) -> None:
    from src.rag.vectorstore import FaissVectorStore

    embeddings = FakeEmbeddings()
    store = FaissVectorStore(str(tmp_path / "faiss"), embeddings)

    retriever = store.as_retriever(k=2)
    assert retriever is not None


def test_vectorstore_build_from_documents(tmp_path: Path) -> None:
    from src.rag.vectorstore import FaissVectorStore

    embeddings = FakeEmbeddings()
    store = FaissVectorStore(str(tmp_path / "faiss"), embeddings)

    docs = [
        Document(page_content="alpha"),
        Document(page_content="beta"),
        Document(page_content="gamma"),
    ]
    count = store.build_from_documents(docs)
    assert count == 3
    assert store.is_index_present()

    stats = store.get_stats()
    assert stats["document_count"] == 3


def test_vectorstore_similarity_search(tmp_path: Path) -> None:
    from src.rag.vectorstore import FaissVectorStore

    embeddings = FakeEmbeddings()
    store = FaissVectorStore(str(tmp_path / "faiss"), embeddings)

    docs = [
        Document(page_content="cat"),
        Document(page_content="dog"),
    ]
    store.build_from_documents(docs)
    results = store.similarity_search("animal", k=2)
    assert len(results) == 2
