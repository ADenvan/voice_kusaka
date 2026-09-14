import time
from typing import Any, Protocol

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from loguru import logger
from typing_extensions import TypedDict

from src.rag.prompts import RAG_PROMPT


class WebSearchTool(Protocol):
    """Protocol for web search tools."""

    def search(self, query: str) -> str: ...


class RAGGraphState(TypedDict):
    """State of the RAG graph."""

    question: str
    generation: str
    documents: list[Document]


def _format_docs(docs: list[Document]) -> str:
    """Format documents into a single string."""
    return "\n\n".join(doc.page_content for doc in docs)


class RAGGraphBuilder:
    """Builder for the simplified RAG LangGraph state machine."""

    def __init__(
        self,
        llm: Any,
        retriever: Any,
        web_search_tool: WebSearchTool,
        use_web_search: bool = True,
    ) -> None:
        self._llm = llm
        self._retriever = retriever
        self._web_search_tool = web_search_tool
        self._use_web_search = use_web_search

    def build(self) -> Any:
        """Build and compile the graph."""
        workflow: StateGraph[RAGGraphState, Any, Any] = StateGraph(RAGGraphState)

        workflow.add_node("retrieve", self._retrieve)
        workflow.add_node("web_search", self._web_search)
        workflow.add_node("generate", self._generate)

        workflow.set_entry_point("retrieve")
        workflow.add_conditional_edges(
            "retrieve",
            self._should_web_search,
            {"web_search": "web_search", "generate": "generate"},
        )
        workflow.add_edge("web_search", "generate")
        workflow.add_edge("generate", END)

        return workflow.compile()

    def _retrieve(self, state: RAGGraphState) -> dict[str, Any]:
        """Retrieve documents from vectorstore."""
        logger.debug("---RETRIEVE---")
        question = state["question"]

        start_time = time.monotonic()
        try:
            documents: list[Document] = self._retriever.invoke(question)
        except Exception as e:
            logger.error("Retriever invoke failed: {}", e)
            documents = []

        elapsed = time.monotonic() - start_time
        logger.debug("Retrieved {} documents in {:.2f}s", len(documents), elapsed)
        return {"documents": documents}

    def _should_web_search(self, state: RAGGraphState) -> str:
        """Route to web search if no documents were retrieved."""
        logger.debug("---DECIDE TO GENERATE---")
        documents = state["documents"]

        if not documents and self._use_web_search:
            logger.debug("---DECISION: WEB SEARCH---")
            return "web_search"

        logger.debug("---DECISION: GENERATE---")
        return "generate"

    def _generate(self, state: RAGGraphState) -> dict[str, Any]:
        """Generate answer from documents."""
        logger.debug("---GENERATE---")
        question = state["question"]
        documents = state["documents"]
        logger.info("RAG generate: question='{}' documents={}", question, len(documents))

        start_time = time.monotonic()
        docs_txt = _format_docs(documents)
        prompt_formatted = RAG_PROMPT.format(context=docs_txt, question=question)
        generation = self._llm.invoke([HumanMessage(content=prompt_formatted)])
        elapsed = time.monotonic() - start_time
        content = getattr(generation, "content", generation)
        logger.info("RAG generation completed in {:.2f}s (chars={})", elapsed, len(str(content)))

        return {"generation": generation}

    def _web_search(self, state: RAGGraphState) -> dict[str, Any]:
        """Perform web search."""
        logger.debug("---WEB SEARCH---")
        question = state["question"]
        documents = list(state.get("documents", []))

        if not self._use_web_search:
            logger.debug("Web search disabled, skipping")
            return {"documents": documents}

        web_results = self._web_search_tool.search(question)
        if web_results:
            web_doc = Document(page_content=web_results)
            documents.append(web_doc)
            logger.debug("Added web search results ({} chars)", len(web_results))

        return {"documents": documents}
