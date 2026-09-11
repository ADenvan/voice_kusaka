import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from voice_ai.core.config import Config
from voice_ai.core.exceptions import LLMConnectionError, LLMTimeoutError
from voice_ai.rag.config import RAGConfig
from voice_ai.rag.embeddings import EmbeddingProvider
from voice_ai.rag.graph import RAGGraphBuilder
from voice_ai.rag.pdf_loader import PDFDocumentLoader
from voice_ai.rag.vectorstore import ChromaVectorStore
from voice_ai.rag.web_search import DuckDuckGoSearchTool

logger = logging.getLogger("voice_ai.rag.agent")


class RAGClient:
    """RAG agent implementing LLMClient protocol."""

    def __init__(self, rag_config: RAGConfig) -> None:
        self._config = rag_config
        self._embedding_provider = EmbeddingProvider(
            rag_config.embedding_model,
            rag_config.embedding_device,
        )
        embeddings = self._embedding_provider.get_embeddings()
        self._vectorstore = ChromaVectorStore(
            rag_config.chroma_persist_dir,
            embeddings,
        )
        self._web_search_tool = DuckDuckGoSearchTool()
        self._llm = self._create_llm()
        self._graph = RAGGraphBuilder(
            self._llm,
            self._vectorstore.as_retriever(rag_config.retriever_k),
            self._web_search_tool,
            rag_config.use_web_search,
        ).build()
        logger.info(
            "RAGClient initialized (model=%s, pdf_dir=%s)",
            rag_config.llm_model,
            rag_config.pdf_directory,
        )

    def _create_llm(self) -> ChatOllama | ChatOpenAI:
        """Create LLM instance for the RAG graph."""
        cfg = self._config
        if cfg.llm_provider == "ollama":
            return ChatOllama(
                model=cfg.llm_model,
                base_url=cfg.llm_base_url,
                temperature=cfg.llm_temperature,
            )
        return ChatOpenAI(
            base_url=cfg.llm_base_url,
            openai_api_key=SecretStr(cfg.llm_api_key),  # type: ignore[call-arg]
            model=cfg.llm_model,
            temperature=cfg.llm_temperature,
        )

    async def chat(self, messages: list[dict[str, str]]) -> str:
        """Get complete answer from RAG agent."""
        question = self._extract_question(messages)
        if not question:
            return "Не удалось понять вопрос."

        inputs = {
            "question": question,
            "max_retries": self._config.max_retries,
            "loop_step": 0,
            "documents": [],
            "generation": "",
            "web_search": "No",
        }

        try:
            result = await asyncio.to_thread(self._run_graph, inputs)
            return result
        except Exception as e:
            error_str = str(e).lower()
            if "connection" in error_str or "connect" in error_str:
                raise LLMConnectionError(
                    f"Cannot reach LLM at {self._config.llm_base_url}"
                ) from e
            if "timeout" in error_str:
                raise LLMTimeoutError("LLM timed out") from e
            logger.error("RAG graph error: %s", e)
            return "Произошла ошибка при обработке запроса."

    async def chat_stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        """For compatibility — yields complete answer as single chunk."""
        result = await self.chat(messages)
        yield result

    def scan_pdf_directory(self, directory: str | None = None) -> int:
        """Scan PDF directory and update vectorstore."""
        dir_to_scan = directory or self._config.pdf_directory
        loader = PDFDocumentLoader(
            self._config.chunk_size,
            self._config.chunk_overlap,
        )
        documents = loader.process_directory(dir_to_scan)
        if not documents:
            logger.warning("No documents found in %s", dir_to_scan)
            return 0

        self._vectorstore.clear()
        return self._vectorstore.add_documents(documents)

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

    def _run_graph(self, inputs: dict[str, Any]) -> str:
        """Run the graph synchronously (to be called via asyncio.to_thread)."""
        for event in self._graph.stream(inputs, stream_mode="values"):
            if "generation" in event:
                gen = event["generation"]
                if hasattr(gen, "content"):
                    return str(gen.content)
                return str(gen)
        return "Не удалось получить ответ."


def create_rag_config(config: Config) -> RAGConfig:
    """Create RAGConfig from main Config."""
    if config.llm_provider == "lmstudio":
        llm_base_url = config.lmstudio_base_url
        llm_model = config.lmstudio_model
        llm_api_key = config.lmstudio_api_key
    else:
        llm_base_url = config.ollama_base_url
        llm_model = config.ollama_model
        llm_api_key = "ollama"

    return RAGConfig(
        pdf_directory=config.rag_pdf_directory,
        chroma_persist_dir=config.rag_chroma_dir,
        embedding_model=config.rag_embedding_model,
        embedding_device=config.rag_embedding_device,
        chunk_size=config.rag_chunk_size,
        chunk_overlap=config.rag_chunk_overlap,
        retriever_k=config.rag_retriever_k,
        max_retries=config.rag_max_retries,
        use_web_search=config.rag_use_web_search,
        llm_provider=config.llm_provider,
        llm_base_url=llm_base_url,
        llm_model=llm_model,
        llm_api_key=llm_api_key,
        llm_temperature=config.rag_llm_temperature,
    )
