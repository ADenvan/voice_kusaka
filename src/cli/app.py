import asyncio
import sys

import typer
from loguru import logger

from src.core.config import Config, config
from src.core.logging_config import setup_logging
from src.core.pipeline import create_pipeline
from src.core.protocols import LLMClient
from src.llm.unified_client import UnifiedLLMClient, check_llm_health
from src.memory.database import SQLiteStore

app = typer.Typer(name="voice_ai", help="Local Russian voice AI assistant")


def get_llm_client(cfg: Config) -> LLMClient:
    """Get LLM client based on provider configuration."""
    return UnifiedLLMClient(cfg)


@app.command()
def run(
    model: str = typer.Option(None, help="LLM model name"),
    provider: str = typer.Option(None, help="LLM provider: ollama, lmstudio"),
    whisper: str = typer.Option(None, help="Whisper model size"),
    device: str = typer.Option(None, help="Whisper device (cuda/cpu)"),
    log_level: str = typer.Option(None, help="Log level"),
    mode: str = typer.Option(None, help="Activation mode: button, wake_word, continuous"),
    lang: str = typer.Option(None, help="Language: ru, en"),
) -> None:
    """Start voice assistant pipeline."""
    overrides = {}
    if model:
        overrides["llm_model"] = model
    if provider:
        if provider not in ("ollama", "lmstudio"):
            print(f"Error: provider must be 'ollama' or 'lmstudio', got '{provider}'")
            raise typer.Exit(code=1)
        overrides["llm_provider"] = provider
        if provider == "ollama":
            overrides["llm_base_url"] = "http://localhost:11434"
            overrides["llm_api_key"] = "ollama"
        else:
            overrides["llm_base_url"] = "http://localhost:1234/v1"
            overrides["llm_api_key"] = "lm-studio"
    if whisper:
        overrides["whisper_model"] = whisper
    if device:
        overrides["whisper_device"] = device
    if log_level:
        overrides["log_level"] = log_level
    if mode:
        if mode not in ("button", "wake_word", "continuous"):
            print(f"Error: mode must be 'button', 'wake_word', or 'continuous', got '{mode}'")
            raise typer.Exit(code=1)
        overrides["activation_mode"] = mode
    if lang:
        if lang not in ("ru", "en"):
            print(f"Error: lang must be 'ru' or 'en', got '{lang}'")
            raise typer.Exit(code=1)
        overrides["tts_language"] = lang

    cfg = Config(_env_file=None, **overrides) if overrides else config
    setup_logging(cfg.log_level)

    logger.info("Starting voice_ai pipeline (mode={})", cfg.activation_mode)
    logger.info("  LLM provider: {}", cfg.llm_provider)
    logger.info("  LLM model: {}", cfg.llm_model)
    logger.info("  Whisper model: {} ({})", cfg.whisper_model, cfg.whisper_device)
    if cfg.activation_mode in ("wake_word", "continuous"):
        logger.info("  Wake word model: {} ({})", cfg.wake_word_model, cfg.wake_word_device)
        logger.info("  Wake word phrases: {}", cfg.wake_word_phrases)

    try:
        asyncio.run(_run_pipeline(cfg))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")


async def _run_pipeline(cfg: Config) -> None:
    await check_llm_health(cfg)
    pipeline = create_pipeline(cfg)
    try:
        await pipeline.run()
    except Exception as e:
        logger.error("Pipeline error: {}", e)
    finally:
        await pipeline.shutdown()


@app.command()
def chat(
    model: str = typer.Option(None, help="LLM model name"),
    provider: str = typer.Option(None, help="LLM provider: ollama, lmstudio"),
) -> None:
    """Text-only chat mode (no microphone/speakers)."""
    overrides = {}
    if model:
        overrides["llm_model"] = model
    if provider:
        if provider not in ("ollama", "lmstudio"):
            print(f"Error: provider must be 'ollama' or 'lmstudio', got '{provider}'")
            raise typer.Exit(code=1)
        overrides["llm_provider"] = provider
        if provider == "ollama":
            overrides["llm_base_url"] = "http://localhost:11434"
            overrides["llm_api_key"] = "ollama"
        else:
            overrides["llm_base_url"] = "http://localhost:1234/v1"
            overrides["llm_api_key"] = "lm-studio"

    cfg = Config(_env_file=None, **overrides) if overrides else config
    setup_logging(cfg.log_level)

    asyncio.run(_text_chat(cfg))


async def _text_chat(cfg: Config) -> None:
    from src.llm.prompt_builder import PromptBuilder
    from src.memory.context import ContextManager

    await check_llm_health(cfg)
    client = get_llm_client(cfg)
    memory = SQLiteStore(cfg)
    prompt_builder = PromptBuilder()
    ContextManager(max_messages=cfg.history_limit)

    session_id = await memory.create_session()
    print(f"Сессия: {session_id}")
    print("Введите 'выход' или 'quit' для завершения.\n")

    try:
        while True:
            user_input = await asyncio.to_thread(input, "Вы: ")
            if user_input.strip().lower() in ("выход", "quit", "exit"):
                break

            await memory.save_message(session_id, "user", user_input)
            history = await memory.get_history(session_id, limit=cfg.history_limit)
            messages = prompt_builder.build_messages(history)

            response_parts: list[str] = []
            sys.stdout.write("Ассистент: ")
            sys.stdout.flush()
            async for token in client.chat_stream(messages):
                sys.stdout.write(token)
                sys.stdout.flush()
                response_parts.append(token)
            print("\n")

            response = "".join(response_parts)
            await memory.save_message(session_id, "assistant", response)
    finally:
        await memory.close()


@app.command()
def models(
    provider: str = typer.Option(None, help="LLM provider: ollama, lmstudio"),
) -> None:
    """List available LLM models."""
    overrides = {}
    if provider:
        if provider not in ("ollama", "lmstudio"):
            print(f"Error: provider must be 'ollama' or 'lmstudio', got '{provider}'")
            raise typer.Exit(code=1)
        overrides["llm_provider"] = provider
        if provider == "ollama":
            overrides["llm_base_url"] = "http://localhost:11434"
            overrides["llm_api_key"] = "ollama"
        else:
            overrides["llm_base_url"] = "http://localhost:1234/v1"
            overrides["llm_api_key"] = "lm-studio"

    cfg = Config(_env_file=None, **overrides) if overrides else config

    async def _list() -> None:
        client = get_llm_client(cfg)
        try:
            model_list = await client.list_models()
            if not model_list:
                if cfg.llm_provider == "lmstudio":
                    print("Нет загруженных моделей в LM Studio.")
                    print("Загрузите модель через интерфейс LM Studio.")
                else:
                    print("Нет установленных моделей.")
                    print("Установите: ollama pull qwen2.5:7b")
            else:
                print(f"Провайдер: {cfg.llm_provider}")
                for m in model_list:
                    print(f"  {m}")
        except Exception as e:
            print(f"Ошибка: {e}")
            if cfg.llm_provider == "lmstudio":
                print("Убедитесь, что LM Studio запущен с локальным сервером.")
            else:
                print("Убедитесь, что Ollama запущен: ollama serve")

    asyncio.run(_list())


@app.command()
def show_config() -> None:
    """Show current configuration."""
    cfg = config
    print(f"  activation_mode:    {cfg.activation_mode}")
    print(f"  llm_provider:       {cfg.llm_provider}")
    print(f"  llm_base_url:       {cfg.llm_base_url}")
    print(f"  llm_model:          {cfg.llm_model}")
    print(f"  llm_api_key:        {cfg.llm_api_key}")
    print(f"  llm_temperature:    {cfg.llm_temperature}")
    print(f"  llm_timeout:        {cfg.llm_timeout}")
    print(f"  llm_max_tokens:     {cfg.llm_max_tokens}")
    print(f"  tts_language:       {cfg.tts_language}")
    print(f"  sample_rate:        {cfg.sample_rate}")
    print(f"  chunk_duration_ms:  {cfg.chunk_duration_ms}")
    print(f"  vad_threshold:      {cfg.vad_threshold}")
    print(f"  whisper_model:      {cfg.whisper_model}")
    print(f"  whisper_device:     {cfg.whisper_device}")
    print(f"  whisper_compute:    {cfg.whisper_compute_type}")
    print(f"  silero_language:    {cfg.silero_language}")
    print(f"  silero_speaker:     {cfg.silero_speaker}")
    print(f"  wake_word_model:    {cfg.wake_word_model}")
    print(f"  wake_word_device:   {cfg.wake_word_device}")
    print(f"  wake_word_phrases:  {cfg.wake_word_phrases}")
    print(f"  wake_word_cooldown: {cfg.wake_word_cooldown_s}s")
    print(f"  wake_word_threshold:{cfg.wake_word_match_threshold}")
    print(f"  output_device:      {cfg.output_device}")
    print(f"  db_path:            {cfg.db_path}")
    print(f"  history_limit:      {cfg.history_limit}")
    print(f"  rag_pdf_directory:  {cfg.rag_pdf_directory}")
    print(f"  rag_faiss_dir:      {cfg.rag_faiss_dir}")
    print(f"  rag_embedding_model:{cfg.rag_embedding_model}")
    print(f"  rag_chunk_size:     {cfg.rag_chunk_size}")
    print(f"  rag_retriever_k:    {cfg.rag_retriever_k}")
    print(f"  rag_use_web_search: {cfg.rag_use_web_search}")
    print(f"  log_level:          {cfg.log_level}")


@app.command()
def rag_scan(
    directory: str = typer.Option(None, help="PDF directory to scan"),
) -> None:
    """Scan PDF directory and update vectorstore."""
    cfg = config
    dir_to_scan = directory or cfg.rag_pdf_directory

    from src.rag.agent import RAGClient, create_rag_config

    rag_config = create_rag_config(cfg)
    client = RAGClient(rag_config)

    print(f"Сканирование: {dir_to_scan}")
    count = client.scan_pdf_directory(dir_to_scan)
    if count > 0:
        print(f"Добавлено чанков: {count}")
    else:
        print("PDF файлы не найдены.")


@app.command()
def rag_query(
    question: str = typer.Argument(..., help="Question to ask"),
    model: str = typer.Option(None, help="LLM model name"),
    provider: str = typer.Option(None, help="LLM provider: ollama, lmstudio"),
) -> None:
    """Query the RAG agent (text mode)."""
    overrides = {}
    if model:
        overrides["llm_model"] = model
    if provider:
        if provider not in ("ollama", "lmstudio"):
            print(f"Error: provider must be 'ollama' or 'lmstudio', got '{provider}'")
            raise typer.Exit(code=1)
        overrides["llm_provider"] = provider
        if provider == "ollama":
            overrides["llm_base_url"] = "http://localhost:11434"
            overrides["llm_api_key"] = "ollama"
        else:
            overrides["llm_base_url"] = "http://localhost:1234/v1"
            overrides["llm_api_key"] = "lm-studio"

    cfg = Config(_env_file=None, **overrides) if overrides else config

    from src.rag.agent import RAGClient, create_rag_config

    rag_config = create_rag_config(cfg)
    client = RAGClient(rag_config)

    messages = [{"role": "user", "content": question}]
    print("Думаю...")
    result = asyncio.run(client.chat(messages))
    print(f"\nОтвет: {result}")


@app.command()
def rag_stats() -> None:
    """Show vectorstore statistics."""
    cfg = config

    from src.rag.agent import RAGClient, create_rag_config

    rag_config = create_rag_config(cfg)
    client = RAGClient(rag_config)

    stats = client.get_stats()
    print(f"  Документов/чанков: {stats['document_count']}")
    print(f"  Хранилище: {stats['index_dir']}")


@app.command()
def rag_clear() -> None:
    """Clear the vectorstore."""
    cfg = config

    from src.rag.agent import RAGClient, create_rag_config

    rag_config = create_rag_config(cfg)
    client = RAGClient(rag_config)

    client.clear_vectorstore()
    print("Vectorstore очищен.")


if __name__ == "__main__":
    app()
