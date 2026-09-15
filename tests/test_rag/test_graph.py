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


def _state(**kwargs: object) -> RAGGraphState:
    """Helper to create RAGGraphState with defaults."""
    defaults: RAGGraphState = {
        "question": "q",
        "generation": "",
        "documents": [],
        "web_search": "No",
        "loop_step": 0,
    }
    defaults.update(kwargs)  # type: ignore[typeddict-item]
    return defaults


@pytest.fixture
def graph_builder() -> RAGGraphBuilder:
    return RAGGraphBuilder(
        llm=FakeLLM(),
        retriever=FakeRetriever([Document(page_content="doc 1")]),
        web_search_tool=FakeWebSearch(),
        use_web_search=True,
    )


@pytest.fixture
def routing_builder() -> RAGGraphBuilder:
    return RAGGraphBuilder(
        llm=FakeLLM('{"datasource": "vectorstore"}'),
        retriever=FakeRetriever([Document(page_content="doc 1")]),
        web_search_tool=FakeWebSearch(),
        use_web_search=True,
        mode="routing",
    )


@pytest.fixture
def full_builder() -> RAGGraphBuilder:
    return RAGGraphBuilder(
        llm=FakeLLM('{"binary_score": "yes"}'),
        retriever=FakeRetriever([Document(page_content="doc 1")]),
        web_search_tool=FakeWebSearch(),
        use_web_search=True,
        mode="full",
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
        "web_search": "No",
        "loop_step": 0,
    }
    assert state["question"] == "test question"
    assert state["generation"] == "test generation"
    assert state["documents"] == []
    assert state["web_search"] == "No"
    assert state["loop_step"] == 0


def test_retrieve_returns_documents(graph_builder: RAGGraphBuilder) -> None:
    state = _state()
    result = graph_builder._retrieve(state)
    assert len(result["documents"]) == 1
    assert result["documents"][0].page_content == "doc 1"


def test_retrieve_handles_exception(graph_builder: RAGGraphBuilder) -> None:
    graph_builder._retriever = FakeRetriever(RuntimeError("retriever failed"))
    state = _state()
    result = graph_builder._retrieve(state)
    assert result["documents"] == []


def test_should_web_search_when_empty(graph_builder: RAGGraphBuilder) -> None:
    state = _state()
    assert graph_builder._should_web_search(state) == "web_search"


def test_should_generate_when_documents(graph_builder: RAGGraphBuilder) -> None:
    state: RAGGraphState = {
        "question": "q",
        "generation": "",
        "documents": [Document(page_content="doc")],
        "web_search": "No",
        "loop_step": 0,
    }
    assert graph_builder._should_web_search(state) == "generate"


def test_should_generate_when_web_search_disabled() -> None:
    builder = RAGGraphBuilder(
        llm=FakeLLM(),
        retriever=FakeRetriever([]),
        web_search_tool=FakeWebSearch(),
        use_web_search=False,
    )
    state = _state()
    assert builder._should_web_search(state) == "generate"


def test_generate_invokes_llm(graph_builder: RAGGraphBuilder) -> None:
    state: RAGGraphState = {
        "question": "what is ai?",
        "generation": "",
        "documents": [Document(page_content="doc 1")],
        "web_search": "No",
        "loop_step": 0,
    }
    result = graph_builder._generate(state)
    assert result["generation"].content == "fake answer"
    assert result["loop_step"] == 1


def test_web_search_adds_results(graph_builder: RAGGraphBuilder) -> None:
    state = _state()
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
    state = _state()
    result = builder._web_search(state)
    assert result["documents"] == []


def test_build_simple_compiles_graph() -> None:
    builder = RAGGraphBuilder(
        llm=FakeLLM(),
        retriever=FakeRetriever([]),
        web_search_tool=FakeWebSearch(),
        use_web_search=True,
        mode="simple",
    )
    graph = builder.build()
    assert graph is not None


def test_build_routing_compiles_graph() -> None:
    builder = RAGGraphBuilder(
        llm=FakeLLM('{"datasource": "vectorstore"}'),
        retriever=FakeRetriever([]),
        web_search_tool=FakeWebSearch(),
        use_web_search=True,
        mode="routing",
    )
    graph = builder.build()
    assert graph is not None


def test_build_full_compiles_graph() -> None:
    builder = RAGGraphBuilder(
        llm=FakeLLM('{"binary_score": "yes"}'),
        retriever=FakeRetriever([]),
        web_search_tool=FakeWebSearch(),
        use_web_search=True,
        mode="full",
    )
    graph = builder.build()
    assert graph is not None


def test_build_unknown_mode_falls_back_to_simple() -> None:
    builder = RAGGraphBuilder(
        llm=FakeLLM(),
        retriever=FakeRetriever([]),
        web_search_tool=FakeWebSearch(),
        use_web_search=True,
        mode="unknown",
    )
    graph = builder.build()
    assert graph is not None


# ──────────────────────────── Routing mode tests ────────────────────────────


def test_route_question_returns_vectorstore(routing_builder: RAGGraphBuilder) -> None:
    state = _state(question="what is python?")
    result = routing_builder._route_question(state)
    assert result == "vectorstore"


def test_route_question_returns_websearch() -> None:
    builder = RAGGraphBuilder(
        llm=FakeLLM('{"datasource": "websearch"}'),
        retriever=FakeRetriever([]),
        web_search_tool=FakeWebSearch(),
        use_web_search=True,
        mode="routing",
    )
    state = _state(question="latest news")
    result = builder._route_question(state)
    assert result == "websearch"


def test_route_question_fallback_on_invalid_json() -> None:
    builder = RAGGraphBuilder(
        llm=FakeLLM("invalid json"),
        retriever=FakeRetriever([]),
        web_search_tool=FakeWebSearch(),
        use_web_search=True,
        mode="routing",
    )
    state = _state()
    result = builder._route_question(state)
    assert result == "vectorstore"


def test_route_question_websearch_disabled() -> None:
    builder = RAGGraphBuilder(
        llm=FakeLLM('{"datasource": "websearch"}'),
        retriever=FakeRetriever([]),
        web_search_tool=FakeWebSearch(),
        use_web_search=False,
        mode="routing",
    )
    state = _state(question="latest news")
    result = builder._route_question(state)
    assert result == "vectorstore"


def test_grade_documents_all_relevant(routing_builder: RAGGraphBuilder) -> None:
    state: RAGGraphState = {
        "question": "q",
        "generation": "",
        "documents": [Document(page_content="doc 1"), Document(page_content="doc 2")],
        "web_search": "No",
        "loop_step": 0,
    }
    result = routing_builder._grade_documents(state)
    assert len(result["documents"]) == 2
    assert result["web_search"] == "No"


def test_grade_documents_some_irrelevant() -> None:
    # Alternate between yes and no
    call_count = [0]

    class AlternateLLM:
        def invoke(self, messages: list[object]) -> MagicMock:
            response = MagicMock()
            call_count[0] += 1
            score = "yes" if call_count[0] % 2 == 1 else "no"
            response.content = f'{{"binary_score": "{score}"}}'
            return response

    builder = RAGGraphBuilder(
        llm=AlternateLLM(),
        retriever=FakeRetriever([]),
        web_search_tool=FakeWebSearch(),
        use_web_search=True,
        mode="routing",
    )
    state: RAGGraphState = {
        "question": "q",
        "generation": "",
        "documents": [Document(page_content="doc 1"), Document(page_content="doc 2")],
        "web_search": "No",
        "loop_step": 0,
    }
    result = builder._grade_documents(state)
    assert len(result["documents"]) == 1
    assert result["web_search"] == "Yes"


def test_grade_documents_all_irrelevant() -> None:
    builder = RAGGraphBuilder(
        llm=FakeLLM('{"binary_score": "no"}'),
        retriever=FakeRetriever([]),
        web_search_tool=FakeWebSearch(),
        use_web_search=True,
        mode="routing",
    )
    state: RAGGraphState = {
        "question": "q",
        "generation": "",
        "documents": [Document(page_content="doc 1")],
        "web_search": "No",
        "loop_step": 0,
    }
    result = builder._grade_documents(state)
    assert len(result["documents"]) == 0
    assert result["web_search"] == "Yes"


def test_decide_to_generate_with_relevant_docs(routing_builder: RAGGraphBuilder) -> None:
    state: RAGGraphState = {
        "question": "q",
        "generation": "",
        "documents": [Document(page_content="doc 1")],
        "web_search": "No",
        "loop_step": 0,
    }
    result = routing_builder._decide_to_generate(state)
    assert result == "generate"


def test_decide_to_generate_with_all_irrelevant() -> None:
    builder = RAGGraphBuilder(
        llm=FakeLLM(),
        retriever=FakeRetriever([]),
        web_search_tool=FakeWebSearch(),
        use_web_search=True,
        mode="routing",
    )
    state: RAGGraphState = {
        "question": "q",
        "generation": "",
        "documents": [],
        "web_search": "Yes",
        "loop_step": 0,
    }
    result = builder._decide_to_generate(state)
    assert result == "websearch"


# ──────────────────────────── Full mode tests ────────────────────────────


def test_grade_generation_useful(full_builder: RAGGraphBuilder) -> None:
    state: RAGGraphState = {
        "question": "q",
        "generation": MagicMock(content="answer"),
        "documents": [Document(page_content="doc 1")],
        "web_search": "No",
        "loop_step": 1,
    }
    result = full_builder._grade_generation(state)
    assert result == "useful"


def test_grade_generation_hallucination_fails() -> None:
    # First call (hallucination) returns no, second call (answer) returns yes
    call_count = [0]

    class HallucinationLLM:
        def invoke(self, messages: list[object]) -> MagicMock:
            response = MagicMock()
            call_count[0] += 1
            score = "no" if call_count[0] == 1 else "yes"
            response.content = f'{{"binary_score": "{score}"}}'
            return response

    builder = RAGGraphBuilder(
        llm=HallucinationLLM(),
        retriever=FakeRetriever([]),
        web_search_tool=FakeWebSearch(),
        use_web_search=True,
        mode="full",
        max_retries=3,
    )
    state: RAGGraphState = {
        "question": "q",
        "generation": MagicMock(content="answer"),
        "documents": [Document(page_content="doc 1")],
        "web_search": "No",
        "loop_step": 1,
    }
    result = builder._grade_generation(state)
    assert result == "not_supported"


def test_grade_generation_answer_fails() -> None:
    # First call (hallucination) returns yes, second call (answer) returns no
    call_count = [0]

    class AnswerLLM:
        def invoke(self, messages: list[object]) -> MagicMock:
            response = MagicMock()
            call_count[0] += 1
            score = "yes" if call_count[0] == 1 else "no"
            response.content = f'{{"binary_score": "{score}"}}'
            return response

    builder = RAGGraphBuilder(
        llm=AnswerLLM(),
        retriever=FakeRetriever([]),
        web_search_tool=FakeWebSearch(),
        use_web_search=True,
        mode="full",
        max_retries=3,
    )
    state: RAGGraphState = {
        "question": "q",
        "generation": MagicMock(content="answer"),
        "documents": [Document(page_content="doc 1")],
        "web_search": "No",
        "loop_step": 1,
    }
    result = builder._grade_generation(state)
    assert result == "not_useful"


def test_grade_generation_max_retries_reached() -> None:
    builder = RAGGraphBuilder(
        llm=FakeLLM('{"binary_score": "no"}'),
        retriever=FakeRetriever([]),
        web_search_tool=FakeWebSearch(),
        use_web_search=True,
        mode="full",
        max_retries=3,
    )
    state: RAGGraphState = {
        "question": "q",
        "generation": MagicMock(content="answer"),
        "documents": [Document(page_content="doc 1")],
        "web_search": "No",
        "loop_step": 3,  # already at max
    }
    result = builder._grade_generation(state)
    assert result == "max_retries"
