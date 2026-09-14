from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from src.rag.agent import RAGClient
from src.rag.config import RAGConfig


class FakeEmbeddings(Embeddings):
    """Fake embeddings for testing."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


@pytest.fixture
def rag_client(tmp_path: Path) -> Iterator[RAGClient]:
    config = RAGConfig(
        faiss_index_dir=str(tmp_path / "faiss"),
        pdf_directory=str(tmp_path / "pdf"),
    )
    with (
        patch("src.rag.agent.EmbeddingProvider") as mock_emb,
        patch("src.rag.agent.FaissVectorStore") as mock_vs,
        patch("src.rag.agent.RAGGraphBuilder") as mock_builder,
    ):
        mock_emb.return_value.get_embeddings.return_value = FakeEmbeddings()
        mock_vs.return_value.is_index_present.return_value = True
        mock_builder.return_value.build.return_value = MagicMock()
        client = RAGClient(config)
        client._vectorstore = mock_vs.return_value
        yield client


def test_extract_question(rag_client: RAGClient) -> None:
    messages = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
        {"role": "user", "content": "question?"},
    ]
    assert rag_client._extract_question(messages) == "question?"


def test_extract_question_empty(rag_client: RAGClient) -> None:
    assert rag_client._extract_question([]) == ""
    assert rag_client._extract_question([{"role": "assistant", "content": "hi"}]) == ""


@pytest.mark.asyncio
async def test_chat_with_mocked_graph(rag_client: RAGClient) -> None:
    def fake_graph(
        inputs: dict[str, object], stream_mode: str = "values"
    ) -> list[dict[str, object]]:
        return [{"generation": MagicMock(content="mocked answer")}]

    rag_client._graph.stream = fake_graph
    result = await rag_client.chat([{"role": "user", "content": "hi"}])
    assert result == "mocked answer"


@pytest.mark.asyncio
async def test_chat_timeout(rag_client: RAGClient) -> None:
    async def timeout_wait_for(
        aw: object, timeout: float
    ) -> object:
        if hasattr(aw, "close"):
            aw.close()
        raise TimeoutError

    rag_client._graph.stream = lambda inputs, stream_mode="values": []
    with patch("src.rag.agent.asyncio.wait_for", timeout_wait_for):
        result = await rag_client.chat([{"role": "user", "content": "hi"}])
    assert "слишком много времени" in result


@pytest.mark.asyncio
async def test_chat_connection_error(rag_client: RAGClient) -> None:
    from src.core.exceptions import LLMConnectionError

    def failing_graph(
        inputs: dict[str, object], stream_mode: str = "values"
    ) -> list[dict[str, object]]:
        raise ConnectionError("cannot connect")

    rag_client._graph.stream = failing_graph
    with pytest.raises(LLMConnectionError):
        await rag_client.chat([{"role": "user", "content": "hi"}])


def test_create_llm_lmstudio() -> None:
    config = RAGConfig(
        llm_provider="lmstudio",
        llm_base_url="http://localhost:1234/v1",
        llm_api_key="lm-studio",
    )
    with (
        patch("src.rag.agent.EmbeddingProvider"),
        patch("src.rag.agent.FaissVectorStore") as mock_vs,
        patch("src.rag.agent.RAGGraphBuilder"),
    ):
        mock_vs.return_value.is_index_present.return_value = True
        client = RAGClient(config)
    llm = client._create_llm()
    assert llm.openai_api_base == "http://localhost:1234/v1"


def test_create_llm_ollama_normalizes_url() -> None:
    config = RAGConfig(
        llm_provider="ollama",
        llm_base_url="http://localhost:11434",
        llm_api_key="ollama",
    )
    with (
        patch("src.rag.agent.EmbeddingProvider"),
        patch("src.rag.agent.FaissVectorStore") as mock_vs,
        patch("src.rag.agent.RAGGraphBuilder"),
    ):
        mock_vs.return_value.is_index_present.return_value = True
        client = RAGClient(config)
    llm = client._create_llm()
    assert llm.openai_api_base == "http://localhost:11434/v1"


def test_get_stats(rag_client: RAGClient) -> None:
    rag_client._vectorstore.get_stats.return_value = {  # type: ignore[attr-defined]
        "document_count": 5,
        "index_dir": "/tmp/faiss",
    }
    stats = rag_client.get_stats()
    assert stats["document_count"] == 5


def test_clear_vectorstore(rag_client: RAGClient) -> None:
    rag_client.clear_vectorstore()
    rag_client._vectorstore.clear.assert_called_once()  # type: ignore[attr-defined]


def test_scan_pdf_directory(rag_client: RAGClient, tmp_path: Path) -> None:
    pdf_dir = tmp_path / "pdf"
    pdf_dir.mkdir()
    rag_client._vectorstore.build_from_documents.return_value = 4  # type: ignore[attr-defined]
    with patch("src.rag.agent.PDFDocumentLoader") as mock_loader:
        mock_loader.return_value.process_directory.return_value = [
            Document(page_content="chunk")
            for _ in range(4)
        ]
        count = rag_client.scan_pdf_directory(str(pdf_dir))
    assert count == 4


@pytest.mark.asyncio
async def test_chat_empty_question(rag_client: RAGClient) -> None:
    result = await rag_client.chat([{"role": "assistant", "content": "hi"}])
    assert result == "Не удалось понять вопрос."


def test_ensure_index_built_builds_from_pdfs(tmp_path: Path) -> None:
    config = RAGConfig(
        faiss_index_dir=str(tmp_path / "faiss"),
        pdf_directory=str(tmp_path / "pdf"),
    )
    with (
        patch("src.rag.agent.EmbeddingProvider") as mock_emb,
        patch("src.rag.agent.FaissVectorStore") as mock_vs,
        patch("src.rag.agent.RAGGraphBuilder"),
        patch("src.rag.agent.PDFDocumentLoader") as mock_loader,
    ):
        mock_emb.return_value.get_embeddings.return_value = FakeEmbeddings()
        mock_vs.return_value.is_index_present.return_value = False
        mock_loader.return_value.process_directory.return_value = [
            Document(page_content="chunk")
        ]
        client = RAGClient(config)

    mock_vs.return_value.build_from_documents.assert_called_once()
    assert client is not None


def test_ensure_index_built_no_pdfs(tmp_path: Path) -> None:
    config = RAGConfig(
        faiss_index_dir=str(tmp_path / "faiss"),
        pdf_directory=str(tmp_path / "pdf"),
    )
    with (
        patch("src.rag.agent.EmbeddingProvider") as mock_emb,
        patch("src.rag.agent.FaissVectorStore") as mock_vs,
        patch("src.rag.agent.RAGGraphBuilder"),
        patch("src.rag.agent.PDFDocumentLoader") as mock_loader,
    ):
        mock_emb.return_value.get_embeddings.return_value = FakeEmbeddings()
        mock_vs.return_value.is_index_present.return_value = False
        mock_loader.return_value.process_directory.return_value = []
        client = RAGClient(config)

    mock_vs.return_value.build_from_documents.assert_not_called()
    assert client is not None


def test_chat_stream_yields_result(rag_client: RAGClient) -> None:
    async def fake_chat(messages: list[dict[str, str]]) -> str:
        return "streamed answer"

    rag_client.chat = fake_chat  # type: ignore[method-assign]

    async def collect() -> list[str]:
        chunks = []
        async for chunk in rag_client.chat_stream([{"role": "user", "content": "hi"}]):
            chunks.append(chunk)
        return chunks

    import asyncio

    chunks = asyncio.run(collect())
    assert chunks == ["streamed answer"]

