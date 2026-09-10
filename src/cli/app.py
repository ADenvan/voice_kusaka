import asyncio
import logging
import sys

import typer

from src.core.config import Config, config
from src.core.logging_config import setup_logging
from src.core.pipeline import create_pipeline
from src.core.protocols import LLMClient
from src.llm.lmstudio_client import LMStudioClient, check_lmstudio_health
from src.llm.ollama_client import OllamaClient, check_ollama_health
from src.memory.database import SQLiteStore

app = typer.Typer(name="voice_ai", help="Local Russian voice AI assistant")


def get_llm_client(cfg: Config) -> LLMClient:
    """Get LLM client based on provider configuration."""
    if cfg.llm_provider == "lmstudio":
        return LMStudioClient(cfg)
    return OllamaClient(cfg)


async def check_llm_health(cfg: Config) -> None:
    """Check LLM provider health based on configuration."""
    if cfg.llm_provider == "lmstudio":
        await check_lmstudio_health(cfg)
    else:
        await check_ollama_health(cfg)


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
        if provider == "lmstudio":
            overrides["lmstudio_model"] = model
        elif provider == "ollama":
            overrides["ollama_model"] = model
        else:
            overrides["ollama_model"] = model
    if provider:
        if provider not in ("ollama", "lmstudio"):
            print(f"Error: provider must be 'ollama' or 'lmstudio', got '{provider}'")
            raise typer.Exit(code=1)
        overrides["llm_provider"] = provider
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
    logger = logging.getLogger("voice_ai")

    logger.info("Starting voice_ai pipeline (mode=%s)", cfg.activation_mode)
    logger.info("  LLM provider: %s", cfg.llm_provider)
    if cfg.llm_provider == "lmstudio":
        logger.info("  LM Studio model: %s", cfg.lmstudio_model)
    else:
        logger.info("  Ollama model: %s", cfg.ollama_model)
    logger.info("  Whisper model: %s (%s)", cfg.whisper_model, cfg.whisper_device)
    if cfg.activation_mode in ("wake_word", "continuous"):
        logger.info("  Wake word model: %s (%s)", cfg.wake_word_model, cfg.wake_word_device)
        logger.info("  Wake word phrases: %s", cfg.wake_word_phrases)

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
        logging.getLogger("voice_ai").error("Pipeline error: %s", e)
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
        if provider == "lmstudio":
            overrides["lmstudio_model"] = model
        elif provider == "ollama":
            overrides["ollama_model"] = model
        else:
            overrides["ollama_model"] = model
    if provider:
        if provider not in ("ollama", "lmstudio"):
            print(f"Error: provider must be 'ollama' or 'lmstudio', got '{provider}'")
            raise typer.Exit(code=1)
        overrides["llm_provider"] = provider

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
    print(f"  tts_language:        {cfg.tts_language}")
    print(f"  sample_rate:         {cfg.sample_rate}")
    print(f"  chunk_duration_ms:   {cfg.chunk_duration_ms}")
    print(f"  vad_threshold:       {cfg.vad_threshold}")
    print(f"  whisper_model:       {cfg.whisper_model}")
    print(f"  whisper_device:      {cfg.whisper_device}")
    print(f"  whisper_compute:      {cfg.whisper_compute_type}")
    print(f"  ollama_base_url:     {cfg.ollama_base_url}")
    print(f"  ollama_model:        {cfg.ollama_model}")
    print(f"  ollama_timeout:      {cfg.ollama_timeout}")
    print(f"  ollama_temperature:  {cfg.ollama_temperature}")
    print(f"  lmstudio_base_url:   {cfg.lmstudio_base_url}")
    print(f"  lmstudio_model:      {cfg.lmstudio_model}")
    print(f"  lmstudio_timeout:    {cfg.lmstudio_timeout}")
    print(f"  lmstudio_temperature:{cfg.lmstudio_temperature}")
    print(f"  silero_language:     {cfg.silero_language}")
    print(f"  silero_speaker:      {cfg.silero_speaker}")
    print(f"  wake_word_model:     {cfg.wake_word_model}")
    print(f"  wake_word_device:    {cfg.wake_word_device}")
    print(f"  wake_word_phrases:   {cfg.wake_word_phrases}")
    print(f"  wake_word_cooldown:  {cfg.wake_word_cooldown_s}s")
    print(f"  wake_word_threshold: {cfg.wake_word_match_threshold}")
    print(f"  output_device:       {cfg.output_device}")
    print(f"  db_path:             {cfg.db_path}")
    print(f"  history_limit:       {cfg.history_limit}")
    print(f"  log_level:           {cfg.log_level}")


if __name__ == "__main__":
    app()