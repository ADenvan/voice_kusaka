import json
import re
import time
from typing import Any, Protocol

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from loguru import logger
from typing_extensions import TypedDict

from src.rag.prompts import (
    ANSWER_GRADER_INSTRUCTIONS,
    ANSWER_GRADER_PROMPT,
    DOC_GRADER_INSTRUCTIONS,
    DOC_GRADER_PROMPT,
    HALLUCINATION_GRADER_INSTRUCTIONS,
    HALLUCINATION_GRADER_PROMPT,
    RAG_PROMPT,
    ROUTER_INSTRUCTIONS,
)


class WebSearchTool(Protocol):
    """Protocol for web search tools."""

    def search(self, query: str) -> str: ...


class RAGGraphState(TypedDict):
    """State of the RAG graph."""

    question: str
    generation: str
    documents: list[Document]
    web_search: str  # "Yes" / "No" (для routing/full)
    loop_step: int  # счётчик итераций (для full)
    feedback: str    # Подсказка для повторной генерации (для full)


def _format_docs(docs: list[Document]) -> str:
    """Format documents into a single string."""
    return "\n\n".join(doc.page_content for doc in docs)


def _safe_json_loads(json_string: str) -> dict[str, Any]:
    """Безопасно извлекает JSON из ответа LLM, удаляя markdown-обертки."""
    try:
        cleaned = re.sub(r"^```json\s*", "", json_string.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error("Не удалось распарсить JSON от LLM. Сырой ответ: {}", json_string)
        raise e


class RAGGraphBuilder:
    """Builder for the RAG LangGraph state machine with configurable modes."""

    def __init__(
        self,
        llm: Any,
        retriever: Any,
        web_search_tool: WebSearchTool,
        use_web_search: bool = True,
        mode: str = "simple",
        max_retries: int = 3,
        router_topics: str = "General knowledge",
    ) -> None:
        self._llm = llm
        self._retriever = retriever
        self._web_search_tool = web_search_tool
        self._use_web_search = use_web_search
        self._mode = mode
        self._max_retries = max_retries
        self._router_topics = router_topics

    def build(self) -> Any:
        """Build and compile the graph based on mode."""
        if self._mode == "simple":
            return self._build_simple()
        elif self._mode == "routing":
            return self._build_routing()
        elif self._mode == "full":
            return self._build_full()
        else:
            logger.warning("Unknown RAG mode '{}', falling back to simple", self._mode)
            return self._build_simple()

    def _build_simple(self) -> Any:
        """Build simple graph: retrieve → (web_search if empty) → generate."""
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

    def _build_routing(self) -> Any:
        """Build routing graph: LLM routes to vectorstore or websearch."""
        workflow: StateGraph[RAGGraphState, Any, Any] = StateGraph(RAGGraphState)

        workflow.add_node("route_question", self._route_question)
        workflow.add_node("retrieve", self._retrieve)
        workflow.add_node("web_search", self._web_search)
        workflow.add_node("grade_documents", self._grade_documents)
        workflow.add_node("generate", self._generate)

        workflow.set_conditional_entry_point(
            self._route_question,
            {"vectorstore": "retrieve", "websearch": "web_search"},
        )
        workflow.add_edge("retrieve", "grade_documents")
        workflow.add_conditional_edges(
            "grade_documents",
            self._decide_to_generate,
            {"generate": "generate", "websearch": "web_search"},
        )
        workflow.add_edge("web_search", "generate")
        workflow.add_edge("generate", END)

        return workflow.compile()

    def _build_full(self) -> Any:
        """Build full graph with grading, retry, and hallucination checks."""
        workflow: StateGraph[RAGGraphState, Any, Any] = StateGraph(RAGGraphState)

        workflow.add_node("route_question", self._route_question)
        workflow.add_node("retrieve", self._retrieve)
        workflow.add_node("web_search", self._web_search)
        workflow.add_node("grade_documents", self._grade_documents)
        workflow.add_node("generate", self._generate)
        workflow.add_node("grade_generation", self._grade_generation)

        workflow.set_conditional_entry_point(
            self._route_question,
            {"vectorstore": "retrieve", "websearch": "web_search"},
        )
        workflow.add_edge("retrieve", "grade_documents")
        workflow.add_conditional_edges(
            "grade_documents",
            self._decide_to_generate,
            {"generate": "generate", "websearch": "web_search"},
        )
        workflow.add_edge("web_search", "generate")
        workflow.add_conditional_edges(
            "generate",
            lambda state: self._grade_generation(state)["decision"],
            {
                "useful": END,
                "not_useful": "web_search",
                "not_supported": "generate",
                "max_retries": END,
            },
        )

        return workflow.compile()

    # ──────────────────────────── Nodes ────────────────────────────

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
        """Route to web search if no documents were retrieved (simple mode only)."""
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
        loop_step = state.get("loop_step", 0)
        feedback = state.get("feedback", "")
        logger.info(
            "RAG generate: question='{}' documents={} loop_step={}",
            question,
            len(documents),
            loop_step,
        )

        start_time = time.monotonic()
        docs_txt = _format_docs(documents)
        
        # Добавляем feedback к промпту, если он есть (для осмысленного retry)
        prompt_formatted = RAG_PROMPT.format(context=docs_txt, question=question)
        if feedback:
            prompt_formatted += f"\n\nIMPORTANT: {feedback}"

        generation = self._llm.invoke([HumanMessage(content=prompt_formatted)])
        elapsed = time.monotonic() - start_time
        content = getattr(generation, "content", generation)
        metadata = getattr(generation, "response_metadata", {}) or {}
        finish_reason = metadata.get("finish_reason") if isinstance(metadata, dict) else None
        usage = metadata.get("token_usage") if isinstance(metadata, dict) else None
        logger.info(
            "RAG generation completed in {:.2f}s (chars={}, finish_reason={}, usage={})",
            elapsed,
            len(str(content)),
            finish_reason,
            usage,
        )

        return {"generation": generation, "loop_step": loop_step + 1}

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

    def _route_question(self, state: RAGGraphState) -> str:
        """Use LLM to route question to vectorstore or websearch."""
        logger.debug("---ROUTE QUESTION---")
        question = state["question"]

        result = self._llm.invoke(
            [
                SystemMessage(content=ROUTER_INSTRUCTIONS.format(topics=self._router_topics)),
                HumanMessage(content=question),
            ]
        )
        content = getattr(result, "content", str(result))

        try:
            source = _safe_json_loads(content)["datasource"]
        except Exception as e:
            logger.warning("Router JSON parse failed: {}, defaulting to vectorstore", e)
            source = "vectorstore"

        if source == "websearch" and self._use_web_search:
            logger.debug("---ROUTE: WEB SEARCH---")
            return "websearch"
        logger.debug("---ROUTE: VECTORSTORE---")
        return "vectorstore"

    def _grade_documents(self, state: RAGGraphState) -> dict[str, Any]:
        """Grade relevance of retrieved documents using LLM."""
        logger.debug("---GRADE DOCUMENTS---")
        question = state["question"]
        documents = state["documents"]

        filtered_docs: list[Document] = []
        web_search = "No"

        for doc in documents:
            prompt = DOC_GRADER_PROMPT.format(document=doc.page_content, question=question)
            result = self._llm.invoke(
                [SystemMessage(content=DOC_GRADER_INSTRUCTIONS), HumanMessage(content=prompt)]
            )
            content = getattr(result, "content", str(result))

            try:
                grade = _safe_json_loads(content)["binary_score"].lower()
            except Exception as e:
                logger.warning("Doc grade JSON parse failed: {}, defaulting to yes", e)
                grade = "yes"

            if grade == "yes":
                filtered_docs.append(doc)
            else:
                web_search = "Yes"

        logger.debug(
            "Document grading: {} relevant, {} filtered, web_search={}",
            len(filtered_docs),
            len(documents) - len(filtered_docs),
            web_search,
        )
        return {"documents": filtered_docs, "web_search": web_search}

    def _decide_to_generate(self, state: RAGGraphState) -> str:
        """Decide whether to generate or go to web search after grading."""
        logger.debug("---DECIDE TO GENERATE (after grading)---")
        web_search = state["web_search"]

        if web_search == "Yes" and self._use_web_search:
            logger.debug("---DECISION: ALL DOCS IRRELEVANT, WEB SEARCH---")
            return "websearch"
        logger.debug("---DECISION: GENERATE---")
        return "generate"

    def _grade_generation(self, state: RAGGraphState) -> dict[str, Any]:
        """Grade generation: check hallucination and answer quality."""
        logger.debug("---GRADE GENERATION---")
        question = state["question"]
        documents = state["documents"]
        generation = state["generation"]
        loop_step = state.get("loop_step", 0)
        max_retries = self._max_retries

        gen_content = getattr(generation, "content", str(generation))

        # 0. Защита от вырожденного цикла: если ответ идентичен предыдущему
        # В текущем LangGraph state мы не храним предыдущую генерацию.
        # Пока ограничимся max_retries=1 и feedback.

        # 1. Check hallucination
        if not documents:
            logger.info("---DECISION: DOCUMENTS EMPTY, SKIPPING HALLUCINATION CHECK---")
            hallucination_grade = "yes"
        else:
            hallucination_prompt = HALLUCINATION_GRADER_PROMPT.format(
                documents=_format_docs(documents), generation=gen_content
            )
            result = self._llm.invoke([
                SystemMessage(content=HALLUCINATION_GRADER_INSTRUCTIONS),
                HumanMessage(content=hallucination_prompt),
            ])
            content = getattr(result, "content", str(result))

            try:
                hallucination_grade = _safe_json_loads(content)["binary_score"].lower()
            except Exception as e:
                logger.warning("Hallucination grade JSON parse failed: {}, defaulting to yes", e)
                hallucination_grade = "yes"

        logger.info("Hallucination grade: {} (loop {})", hallucination_grade, loop_step)

        if hallucination_grade == "yes":
            # 2. Check answer quality
            answer_prompt = ANSWER_GRADER_PROMPT.format(
                question=question, generation=gen_content
            )
            result = self._llm.invoke([
                SystemMessage(content=ANSWER_GRADER_INSTRUCTIONS),
                HumanMessage(content=answer_prompt),
            ])
            content = getattr(result, "content", str(result))

            try:
                answer_grade = _safe_json_loads(content)["binary_score"].lower()
            except Exception as e:
                logger.warning("Answer grade JSON parse failed: {}, defaulting to yes", e)
                answer_grade = "yes"

            logger.info("Answer grade: {} (loop {})", answer_grade, loop_step)

            if answer_grade == "yes":
                logger.info("---DECISION: GENERATION USEFUL---")
                return {"decision": "useful"}

            # Answer quality failed → web search for better info
            if loop_step < max_retries:
                logger.info("---DECISION: GENERATION NOT USEFUL, WEB SEARCH---")
                return {"decision": "not_useful"}
            logger.info("---DECISION: MAX RETRIES REACHED---")
            return {"decision": "max_retries"}

        # Hallucination failed → retry generation with feedback
        if loop_step < max_retries:
            logger.info("---DECISION: GENERATION NOT GROUNDED, RETRY WITH FEEDBACK---")
            return {
                "decision": "not_supported",
                "feedback": (
                    "Your previous answer was not grounded in the provided facts. "
                    "Please answer STRICTLY based on the context."
                ),
            }
        logger.info("---DECISION: MAX RETRIES REACHED---")
        return {"decision": "max_retries"}
