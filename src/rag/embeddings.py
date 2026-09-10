import logging

from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger("voice_ai.rag.embeddings")


class EmbeddingProvider:
    """Provider for embedding models."""

    def __init__(self, model_name: str, device: str = "cpu") -> None:
        self._model_name = model_name
        self._device = device
        self._embeddings: HuggingFaceEmbeddings | None = None

    def get_embeddings(self) -> Embeddings:
        """Get or create the embeddings instance."""
        if self._embeddings is None:
            logger.info("Loading embedding model: %s (device=%s)", self._model_name, self._device)
            self._embeddings = HuggingFaceEmbeddings(
                model_name=self._model_name,
                model_kwargs={"device": self._device},
            )
            logger.info("Embedding model loaded")
        return self._embeddings
