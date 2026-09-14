from unittest.mock import MagicMock

import pytest
from langchain_core.documents import Document

from src.rag.graph import RAGGraphBuilder, RAGGraphState, _format_docs


class FakeLLM:
    """Fake LLM that returns a predefined response."""

    def __init__(self, content: str = "fake answer") -> None:
        self._content = content

    def invoke(self, messages: list[object]) -> MagicMock:
        response = MagicMock()
        response.content = self._content
        return response


class FakeRetriever:
    """Fake retriever returning predefined documents."""

    def __init__(self, documents: list[Document] | Exception) -> None:
        self._documents = documents

    def invoke(self, question: str) -> list[Document]:
        if isinstance(self._documents, Exception):
            raise self._documents
        return self._documents


class FakeWebSearch:
    """Fake web search returning a fixed string."""

    def __init__(self, result: str = "web result") -> None:
        self._result = result

    def search(self, query: str) -> str:
        return self._result


@pytest.fixture
def graph_builder() -> RAGGraphBuilder:
    return RAGGraphBuilder(
        llm=FakeLLM(),
        retriever=FakeRetriever([Document(page_content="doc 1")]),
        web_search_tool=FakeWebSearch(),
        use_web_search=True,
    )


def test_format_docs() -> None:
    docs = [
        Document(page_content="doc 1"),
        Document(page_content="doc 2"),
    ]
    result = _format_docs(docs)
    assert result == "doc 1\n\ndoc 2"


def test_format_docs_empty() -> None:
    result = _format_docs([])
    assert result == ""


def test_rag_graph_state_typed_dict() -> None:
    state: RAGGraphState = {
        "question": "test question",
        "generation": "test generation",
        "documents": [],
    }
    assert state["question"] == "test question"
    assert state["generation"] == "test generation"
    assert state["documents"] == []


def test_retrieve_returns_documents(graph_builder: RAGGraphBuilder) -> None:
    state: RAGGraphState = {"question": "q", "generation": "", "documents": []}
    result = graph_builder._retrieve(state)
    assert len(result["documents"]) == 1
    assert result["documents"][0].page_content == "doc 1"


def test_retrieve_handles_exception(graph_builder: RAGGraphBuilder) -> None:
    graph_builder._retriever = FakeRetriever(RuntimeError("retriever failed"))
    state: RAGGraphState = {"question": "q", "generation": "", "documents": []}
    result = graph_builder._retrieve(state)
    assert result["documents"] == []


def test_should_web_search_when_empty(graph_builder: RAGGraphBuilder) -> None:
    state: RAGGraphState = {"question": "q", "generation": "", "documents": []}
    assert graph_builder._should_web_search(state) == "web_search"


def test_should_generate_when_documents(graph_builder: RAGGraphBuilder) -> None:
    state: RAGGraphState = {
        "question": "q",
        "generation": "",
        "documents": [Document(page_content="doc")],
    }
    assert graph_builder._should_web_search(state) == "generate"


def test_should_generate_when_web_search_disabled() -> None:
    builder = RAGGraphBuilder(
        llm=FakeLLM(),
        retriever=FakeRetriever([]),
        web_search_tool=FakeWebSearch(),
        use_web_search=False,
    )
    state: RAGGraphState = {"question": "q", "generation": "", "documents": []}
    assert builder._should_web_search(state) == "generate"


def test_generate_invokes_llm(graph_builder: RAGGraphBuilder) -> None:
    state: RAGGraphState = {
        "question": "what is ai?",
        "generation": "",
        "documents": [Document(page_content="doc 1")],
    }
    result = graph_builder._generate(state)
    assert result["generation"].content == "fake answer"


def test_web_search_adds_results(graph_builder: RAGGraphBuilder) -> None:
    state: RAGGraphState = {"question": "q", "generation": "", "documents": []}
    result = graph_builder._web_search(state)
    assert len(result["documents"]) == 1
    assert result["documents"][0].page_content == "web result"


def test_web_search_skips_when_disabled() -> None:
    builder = RAGGraphBuilder(
        llm=FakeLLM(),
        retriever=FakeRetriever([]),
        web_search_tool=FakeWebSearch(),
        use_web_search=False,
    )
    state: RAGGraphState = {"question": "q", "generation": "", "documents": []}
    result = builder._web_search(state)
    assert result["documents"] == []


def test_build_compiles_graph() -> None:
    builder = RAGGraphBuilder(
        llm=FakeLLM(),
        retriever=FakeRetriever([]),
        web_search_tool=FakeWebSearch(),
        use_web_search=True,
    )
    graph = builder.build()
    assert graph is not None
