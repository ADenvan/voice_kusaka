import json
import logging
import operator
import re
from typing import Annotated, Any

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
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
from src.rag.web_search import DuckDuckGoSearchTool

logger = logging.getLogger("voice_ai.rag.graph")


class RAGGraphState(TypedDict):
    """State of the RAG graph."""

    question: str
    generation: str
    web_search: str
    max_retries: int
    loop_step: Annotated[int, operator.add]
    documents: list[Document]


def _safe_json_loads(json_string: str) -> dict[str, Any]:
    """Safely extract JSON from LLM response, removing markdown wrappers."""
    try:
        cleaned = re.sub(r"^```json\s*", "", json_string.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            result: dict[str, Any] = json.loads(match.group())
            return result
        result = json.loads(cleaned)
        return result
    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON from LLM. Raw: %s", json_string[:200])
        raise e


def _format_docs(docs: list[Document]) -> str:
    """Format documents into a single string."""
    return "\n\n".join(doc.page_content for doc in docs)


class RAGGraphBuilder:
    """Builder for the RAG LangGraph state machine."""

    def __init__(
        self,
        llm: Any,
        retriever: Any,
        web_search_tool: DuckDuckGoSearchTool,
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
        workflow.add_node("grade_documents", self._grade_documents)
        workflow.add_node("generate", self._generate)
        workflow.add_node("web_search", self._web_search)

        workflow.set_conditional_entry_point(
            self._route_question,
            {"websearch": "web_search", "vectorstore": "retrieve"},
        )
        workflow.add_edge("web_search", "generate")
        workflow.add_edge("retrieve", "grade_documents")
        workflow.add_conditional_edges(
            "grade_documents",
            self._decide_to_generate,
            {"websearch": "web_search", "generate": "generate"},
        )
        workflow.add_conditional_edges(
            "generate",
            self._grade_generation,
            {
                "not supported": "generate",
                "useful": END,
                "not useful": "web_search",
                "max retries": END,
            },
        )

        return workflow.compile()

    def _route_question(self, state: RAGGraphState) -> str:
        """Route question to web search or vectorstore."""
        logger.debug("---ROUTE QUESTION---")
        try:
            messages = [
                SystemMessage(content=ROUTER_INSTRUCTIONS),
                HumanMessage(content=state["question"]),
            ]
            result = self._llm.invoke(messages)
            source = _safe_json_loads(str(result.content))["datasource"]
            if source == "websearch":
                logger.debug("---ROUTE TO WEB SEARCH---")
                return "websearch"
        except Exception as e:
            logger.warning("Router failed: %s, defaulting to vectorstore", e)
        logger.debug("---ROUTE TO VECTORSTORE---")
        return "vectorstore"

    def _retrieve(self, state: RAGGraphState) -> dict[str, Any]:
        """Retrieve documents from vectorstore."""
        logger.debug("---RETRIEVE---")
        question = state["question"]
        documents = self._retriever.invoke(question)
        logger.debug("Retrieved %d documents", len(documents))
        return {"documents": documents}

    def _grade_documents(self, state: RAGGraphState) -> dict[str, Any]:
        """Grade documents for relevance."""
        logger.debug("---GRADE DOCUMENTS---")
        question = state["question"]
        documents = state["documents"]

        filtered_docs: list[Document] = []
        web_search = "No"

        for d in documents:
            try:
                prompt_formatted = DOC_GRADER_PROMPT.format(
                    document=d.page_content, question=question
                )
                messages = [
                    SystemMessage(content=DOC_GRADER_INSTRUCTIONS),
                    HumanMessage(content=prompt_formatted),
                ]
                result = self._llm.invoke(messages)
                grade = _safe_json_loads(str(result.content))["binary_score"]
                if grade.lower() == "yes":
                    logger.debug("---DOC RELEVANT---")
                    filtered_docs.append(d)
                else:
                    logger.debug("---DOC NOT RELEVANT---")
                    web_search = "Yes"
            except Exception as e:
                logger.warning("Document grading failed: %s, keeping doc", e)
                filtered_docs.append(d)

        return {"documents": filtered_docs, "web_search": web_search}

    def _generate(self, state: RAGGraphState) -> dict[str, Any]:
        """Generate answer from documents."""
        logger.debug("---GENERATE---")
        question = state["question"]
        documents = state["documents"]

        docs_txt = _format_docs(documents)
        prompt_formatted = RAG_PROMPT.format(context=docs_txt, question=question)
        generation = self._llm.invoke([HumanMessage(content=prompt_formatted)])

        return {"generation": generation, "loop_step": 1}

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
            logger.debug("Added web search results (%d chars)", len(web_results))

        return {"documents": documents}

    def _decide_to_generate(self, state: RAGGraphState) -> str:
        """Decide whether to generate or search web."""
        logger.debug("---DECIDE TO GENERATE---")
        web_search = state["web_search"]

        if web_search == "Yes":
            logger.debug("---DECISION: WEB SEARCH---")
            return "websearch"
        logger.debug("---DECISION: GENERATE---")
        return "generate"

    def _grade_generation(self, state: RAGGraphState) -> str:
        """Grade generation for hallucination and answer quality."""
        logger.debug("---GRADE GENERATION---")
        question = state["question"]
        documents = state["documents"]
        generation = state["generation"]
        max_retries = state.get("max_retries", 3)
        loop_step = state.get("loop_step", 0)

        gen_content = generation.content if hasattr(generation, "content") else str(generation)

        try:
            hall_prompt = HALLUCINATION_GRADER_PROMPT.format(
                documents=_format_docs(documents), generation=gen_content
            )
            messages = [
                SystemMessage(content=HALLUCINATION_GRADER_INSTRUCTIONS),
                HumanMessage(content=hall_prompt),
            ]
            result = self._llm.invoke(messages)
            hall_grade = _safe_json_loads(str(result.content))["binary_score"]
        except Exception as e:
            logger.warning("Hallucination grading failed: %s", e)
            return "useful"

        if hall_grade == "yes":
            logger.debug("---GENERATION GROUNDED IN DOCS---")
            try:
                ans_prompt = ANSWER_GRADER_PROMPT.format(
                    question=question, generation=gen_content
                )
                messages = [
                    SystemMessage(content=ANSWER_GRADER_INSTRUCTIONS),
                    HumanMessage(content=ans_prompt),
                ]
                result = self._llm.invoke(messages)
                ans_grade = _safe_json_loads(str(result.content))["binary_score"]
            except Exception as e:
                logger.warning("Answer grading failed: %s", e)
                return "useful"

            if ans_grade == "yes":
                logger.debug("---GENERATION ADDRESSES QUESTION---")
                return "useful"
            if loop_step <= max_retries:
                logger.debug("---GENERATION DOES NOT ADDRESS QUESTION---")
                return "not useful"
            logger.debug("---MAX RETRIES REACHED---")
            return "max retries"

        if loop_step <= max_retries:
            logger.debug("---GENERATION NOT GROUNDED, RETRY---")
            return "not supported"
        logger.debug("---MAX RETRIES REACHED---")
        return "max retries"
