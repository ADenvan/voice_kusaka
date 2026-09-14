from unittest.mock import MagicMock, patch

from src.rag.embeddings import EmbeddingProvider


def test_get_embeddings_loads_model_once() -> None:
    provider = EmbeddingProvider("intfloat/multilingual-e5-large", device="cpu")
    with patch("src.rag.embeddings.HuggingFaceEmbeddings") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        embeddings = provider.get_embeddings()
        assert embeddings is mock_instance
        mock_cls.assert_called_once_with(
            model_name="intfloat/multilingual-e5-large",
            model_kwargs={"device": "cpu"},
        )

        embeddings2 = provider.get_embeddings()
        assert embeddings2 is mock_instance
        mock_cls.assert_called_once()


def test_get_embeddings_with_cuda() -> None:
    provider = EmbeddingProvider("sentence-transformers/all-MiniLM-L6-v2", device="cuda")
    with patch("src.rag.embeddings.HuggingFaceEmbeddings") as mock_cls:
        mock_cls.return_value = MagicMock()
        provider.get_embeddings()
        mock_cls.assert_called_once_with(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cuda"},
        )
