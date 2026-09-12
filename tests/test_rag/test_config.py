from src.rag.config import RAGConfig


def test_rag_config_defaults() -> None:
    config = RAGConfig()
    assert config.pdf_directory == "data/pdf"
    assert config.chroma_persist_dir == "data/chroma_db"
    assert config.embedding_model == "intfloat/multilingual-e5-large"
    assert config.embedding_device == "cpu"
    assert config.chunk_size == 1024
    assert config.chunk_overlap == 200
    assert config.retriever_k == 3
    assert config.max_retries == 3
    assert config.use_web_search is True
    assert config.llm_temperature == 0.0


def test_rag_config_custom_values() -> None:
    config = RAGConfig(
        pdf_directory="custom/pdf",
        chroma_persist_dir="custom/chroma",
        chunk_size=512,
        retriever_k=5,
        llm_model="custom-model",
    )
    assert config.pdf_directory == "custom/pdf"
    assert config.chroma_persist_dir == "custom/chroma"
    assert config.chunk_size == 512
    assert config.retriever_k == 5
    assert config.llm_model == "custom-model"
