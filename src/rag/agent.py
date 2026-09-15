import asyncio
from collections.abc import AsyncIterator
from typing import Any

from langchain_openai import ChatOpenAI
from loguru import logger
from pydantic import SecretStr

from src.core.config import Config
from src.core.exceptions import LLMConnectionError, LLMTimeoutError
from src.rag.config import RAGConfig
from src.rag.embeddings import EmbeddingProvider
from src.rag.graph import RAGGraphBuilder
from src.rag.pdf_loader import PDFDocumentLoader
from src.rag.vectorstore import FaissVectorStore
from src.rag.web_search import DuckDuckGoSearchTool


class RAGClient:
    """RAG agent implementing LLMClient protocol."""

    def __init__(
        self,
        rag_config: RAGConfig,
        router_topics: str = "",
    ) -> None:
        self._config = rag_config
        self._embedding_provider = EmbeddingProvider(
            rag_config.embedding_model,
            rag_config.embedding_device,
        )
        embeddings = self._embedding_provider.get_embeddings()
        self._vectorstore = FaissVectorStore(
            rag_config.faiss_index_dir,
            embeddings,
        )
        self._web_search_tool = DuckDuckGoSearchTool()
        self._llm = self._create_llm()

        self._ensure_index_built()

        topics = self._get_topics(router_topics)
        logger.info("RAG router topics: {}", topics)

        self._graph = RAGGraphBuilder(
            self._llm,
            self._vectorstore.as_retriever(rag_config.retriever_k),
            self._web_search_tool,
            rag_config.use_web_search,
            mode=rag_config.mode,
            max_retries=rag_config.max_retries,
            router_topics=topics,
        ).build()
        logger.info(
            "RAGClient initialized (model={}, pdf_dir={}, faiss_index={})",
            rag_config.llm_model,
            rag_config.pdf_directory,
            rag_config.faiss_index_dir,
        )

    def _create_llm(self) -> ChatOpenAI:
        """Create ChatOpenAI instance for the RAG graph."""
        cfg = self._config
        if cfg.llm_provider == "ollama":
            base_url = cfg.llm_base_url.rstrip("/")
            if not base_url.endswith("/v1"):
                base_url = base_url + "/v1"
        else:
            base_url = cfg.llm_base_url

        return ChatOpenAI(
            base_url=base_url,
            openai_api_key=SecretStr(cfg.llm_api_key),  # type: ignore[call-arg]
            model=cfg.llm_model,
            temperature=cfg.llm_temperature,
            max_tokens=cfg.llm_max_tokens,
            request_timeout=cfg.llm_timeout,
        )

    def _get_topics(self, provided_topics: str) -> str:
        """Resolve router topics from config or PDF filenames."""
        if provided_topics and provided_topics.strip():
            return provided_topics.strip()

        import os
        pdf_dir = self._config.pdf_directory
        if not os.path.exists(pdf_dir):
            return "General knowledge"

        files = [f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")]
        if not files:
            return "General knowledge"

        return ", ".join(files)
    
    def _ensure_index_built(self) -> None:
        """Load existing FAISS index or build one from PDFs."""
        if self._vectorstore.is_index_present():
            logger.info("FAISS index found at {}", self._config.faiss_index_dir)
            stats = self._vectorstore.get_stats()
            logger.info("FAISS index stats: {}", stats)
            return

        logger.warning(
            "FAISS index not found at {}. Building from PDFs in {}...",
            self._config.faiss_index_dir,
            self._config.pdf_directory,
        )
        loader = PDFDocumentLoader(
            self._config.chunk_size,
            self._config.chunk_overlap,
        )
        documents = loader.process_directory(self._config.pdf_directory)
        if documents:
            self._vectorstore.build_from_documents(documents)
        else:
            logger.warning("No PDF documents found in {}", self._config.pdf_directory)

    async def chat(self, messages: list[dict[str, str]]) -> str:
        """Get complete answer from RAG agent."""
        question = self._extract_question(messages)
        if not question:
            return "Не удалось понять вопрос."

        inputs = {
            "question": question,
            "documents": [],
            "generation": "",
            "web_search": "No",
            "loop_step": 0,
        }

        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(self._run_graph, inputs),
                timeout=self._config.timeout,
            )
            return result
        except TimeoutError:
            logger.error("RAG graph timed out after 60s")
            return "Ответ занял слишком много времени. Попробуйте ещё раз."
        except Exception as e:
            error_str = str(e).lower()
            if "connection" in error_str or "connect" in error_str:
                raise LLMConnectionError(
                    f"Cannot reach LLM at {self._config.llm_base_url}"
                ) from e
            if "timeout" in error_str:
                raise LLMTimeoutError("LLM timed out") from e
            logger.error("RAG graph error: {}", e)
            return "Произошла ошибка при обработке запроса."

    async def chat_stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        """For compatibility — yields complete answer as single chunk."""
        result = await self.chat(messages)
        yield result

    def scan_pdf_directory(self, directory: str | None = None) -> int:
        """Scan PDF directory and rebuild the FAISS index."""
        dir_to_scan = directory or self._config.pdf_directory
        loader = PDFDocumentLoader(
            self._config.chunk_size,
            self._config.chunk_overlap,
        )
        documents = loader.process_directory(dir_to_scan)
        if not documents:
            logger.warning("No documents found in {}", dir_to_scan)
            return 0

        return self._vectorstore.build_from_documents(documents)

    def get_stats(self) -> dict[str, int | str]:
        """Get vectorstore statistics."""
        return self._vectorstore.get_stats()

    def clear_vectorstore(self) -> None:
        """Clear the vectorstore."""
        self._vectorstore.clear()

    def _extract_question(self, messages: list[dict[str, str]]) -> str:
        """Extract the last user message as the question."""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return msg.get("content", "")
        return ""

    def _extract_content(self, generation: Any) -> str:
        """Extract text from generation, with reasoning model fallback."""
        text = generation.content if hasattr(generation, "content") else str(generation)

        if isinstance(text, str) and text.strip():
            return text.strip()

        # Reasoning models (e.g. QwQ/qwen-reasoning) may put answer in reasoning_content
        reasoning = ""
        if hasattr(generation, "additional_kwargs"):
            reasoning = generation.additional_kwargs.get("reasoning_content") or ""
        if not reasoning and hasattr(generation, "response_metadata"):
            reasoning = generation.response_metadata.get("reasoning_content") or ""
        if isinstance(reasoning, str) and reasoning.strip():
            logger.info("Using reasoning_content as answer ({} chars)", len(reasoning))
            return reasoning.strip()

        return ""

    def _run_graph(self, inputs: dict[str, Any]) -> str:
        """Run the graph synchronously (to be called via asyncio.to_thread)."""
        logger.info("RAG graph started for question: {}", inputs.get("question"))
        final_answer = ""
        for event in self._graph.stream(inputs, stream_mode="values"):
            gen = event.get("generation")
            if gen is None:
                continue
            content = self._extract_content(gen)
            if content:
                final_answer = content
                logger.info("RAG graph produced answer ({} chars)", len(content))

        if final_answer:
            return final_answer

        logger.warning("RAG graph finished without generation")
        return "Не удалось получить ответ."


def create_rag_config(config: Config) -> RAGConfig:
    """Create RAGConfig from main Config."""
    return RAGConfig(
        pdf_directory=config.rag_pdf_directory,
        faiss_index_dir=config.rag_faiss_dir,
        embedding_model=config.rag_embedding_model,
        embedding_device=config.rag_embedding_device,
        chunk_size=config.rag_chunk_size,
        chunk_overlap=config.rag_chunk_overlap,
        retriever_k=config.rag_retriever_k,
        max_retries=config.rag_max_retries,
        use_web_search=config.rag_use_web_search,
        llm_provider=config.llm_provider,
        llm_base_url=config.llm_base_url,
        llm_model=config.llm_model,
        llm_api_key=config.llm_api_key,
        llm_temperature=config.rag_llm_temperature,
        llm_max_tokens=config.llm_max_tokens,
        llm_timeout=config.llm_timeout,
        mode=config.rag_mode,
        timeout=config.rag_timeout,
        router_topics=config.rag_router_topics,
    )
