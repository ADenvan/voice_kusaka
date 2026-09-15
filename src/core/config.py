from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    sample_rate: int = 16000
    chunk_duration_ms: int = 500
    vad_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    vad_min_speech_duration_ms: int = 250
    vad_min_silence_duration_ms: int = 100
    vad_speech_pad_ms: int = 300

    whisper_model: str = "large-v3"
    whisper_device: str = "cuda"
    whisper_compute_type: str = "float16"

    llm_provider: str = "lmstudio"
    llm_model: str = "qwen2.5-coder-7b-instruct"
    llm_api_key: str = "lmstudio"
    llm_base_url: str = "http://localhost:1234/v1"

    # llm_provider: str = "ollama"
    # llm_model: str = "qwen2.5:7b"
    # llm_api_key: str = "ollama"
    # llm_base_url: str = "http://localhost:11434"
    llm_temperature: float = 0.7
    llm_timeout: int = 60
    llm_max_tokens: int = 256

    tts_language: str = "ru"

    silero_language: str = "ru"
    silero_speaker: str = "v5_ru"
    silero_voice: str = "baya"
    silero_sample_rate: int = 48000

    silero_en_language: str = "en"
    silero_en_speaker: str = "v3_en"
    silero_en_voice: str = "en_0"
    silero_en_sample_rate: int = 48000

    output_device: int | None = None

    activation_mode: str = "wake_word"
    wake_word_model: str = "base"
    wake_word_device: str = "cpu"
    wake_word_compute_type: str = "int8"
    wake_word_phrases: list[str] = ["войс ай", "voice ai", "войсай", "войс айай"]
    wake_word_cooldown_s: float = 3.0
    wake_word_match_threshold: float = 0.7

    db_path: str = "data/voice_ai.db"
    history_limit: int = 50

    rag_pdf_directory: str = "data/pdf"
    rag_faiss_dir: str = "data/faiss_index"
    rag_embedding_model: str = "intfloat/multilingual-e5-large"
    rag_embedding_device: str = "cpu"
    rag_chunk_size: int = 1024
    rag_chunk_overlap: int = 200
    rag_retriever_k: int = 3
    rag_max_retries: int = 3
    rag_use_web_search: bool = True
    rag_llm_temperature: float = 0.0
    rag_mode: str = "simple"  # "simple" | "routing" | "full"
    rag_timeout: int = 180

    log_level: str = "INFO"


config = Config()
