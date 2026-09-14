from pydantic import BaseModel


class RAGConfig(BaseModel):
    """Configuration for the RAG agent."""

    pdf_directory: str = "data/pdf"
    faiss_index_dir: str = "data/faiss_index"

    embedding_model: str = "intfloat/multilingual-e5-large"
    embedding_device: str = "cpu"

    chunk_size: int = 1024
    chunk_overlap: int = 200

    retriever_k: int = 3
    max_retries: int = 3
    use_web_search: bool = True

    llm_provider: str = "lmstudio"
    llm_base_url: str = "http://localhost:1234/v1"
    llm_model: str = "qwen2.5-coder-7b-instruct"
    llm_api_key: str = "lm-studio"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 512
    llm_timeout: int = 60
