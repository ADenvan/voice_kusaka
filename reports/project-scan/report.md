# Отчёт проекта: voice_ai

**Дата сканирования:** 2026-04-17
**Корень проекта:** voice_ai

---

## Общее описание

**voice_ai** — локальный русскоязычный голосовой AI-ассистент с полным конвейером обработки речи: Микрофон → VAD → STT (faster-whisper) → LLM (Ollama/qwen2.5) → TTS (Silero) → Динамики. Проект написан на Python 3.13 с использованием async/await архитектуры, Protocol-интерфейсов для dependency injection и pydantic-settings для конфигурации. Включает CLI-интерфейс (Typer), SQLite-хранилище истории (aiosqlite), 51 юнит- и интеграционный тест.

## Структура проекта

```
voice_ai/
├── .opencode/ — Конфигурационная папка OpenCode (агенты, навыки, команды, плагины)
├── .vscode/ — Настройки VS Code для pytest
│   └── settings.json — Конфигурация запуска тестов через pytest
├── data/ — Хранилище данных (SQLite база)
│   └── voice_ai.db — База данных SQLite для истории диалогов
├── reports/ — Отчёты и логи
│   ├── mvp-implementation-report.md — Отчёт о реализации MVP (283 строки)
│   ├── project-scan/ — Папка отчётов сканирования
│   │   └── report.md — Данный отчёт
│   └── prompt_log.txt — Файл логирования промптов (пока пуст)
├── scripts/ — Диагностические скрипты
│   └── test_mic.py — Скрипт диагностики микрофона и VAD (176 строк)
├── src/ — Основной исходный код проекта
│   ├── __init__.py — Пустой пакетный файл
│   ├── api/ — Зарезервировано для Phase 2 (FastAPI REST/WebSocket)
│   │   └── __init__.py — Пустой пакетный файл
│   ├── audio/ — Модуль аудиоввода/вывода и VAD
│   │   ├── __init__.py — Пустой пакетный файл
│   │   ├── input.py — Захват аудио с микрофона через sounddevice (107 строк)
│   │   ├── output.py — Воспроизведение аудио через sounddevice + ресемплинг (50 строк)
│   │   └── vad.py — Silero VAD и EnergyVAD (fallback) для детекции речи (78 строк)
│   ├── cli/ — CLI-интерфейс на Typer
│   │   ├── __init__.py — Пустой пакетный файл
│   │   └── app.py — Typer CLI с командами run, chat, models, show-config (166 строк)
│   ├── core/ — Ядро проекта: конфигурация, исключения, пайплайн, протоколы
│   │   ├── __init__.py — Пустой пакетный файл
│   │   ├── config.py — Конфигурация через pydantic-settings с .env (41 строка)
│   │   ├── exceptions.py — Иерархия исключений проекта (38 строк)
│   │   ├── pipeline.py — Оркестратор конвейера (state machine, DI) (208 строк)
│   │   └── protocols.py — Protocol-интерфейсы и типы данных (69 строк)
│   ├── llm/ — Модуль взаимодействия с LLM (Ollama)
│   │   ├── __init__.py — Пустой пакетный файл
│   │   ├── ollama_client.py — Асинхронный клиент Ollama (streaming + health check) (114 строк)
│   │   └── prompt_builder.py — Построение сообщений с системным промптом (24 строки)
│   ├── memory/ — Модуль памяти (SQLite + контекст)
│   │   ├── __init__.py — Пустой пакетный файл
│   │   ├── context.py — Обрезка истории и оценка токенов (31 строка)
│   │   └── database.py — Асинхронное SQLite-хранилище (aiosqlite, WAL) (97 строк)
│   ├── stt/ — Модуль распознавания речи (Speech-to-Text)
│   │   ├── __init__.py — Пустой пакетный файл
│   │   └── whisper_engine.py — faster-whisper движок с ленивой загрузкой (57 строк)
│   └── tts/ — Модуль синтеза речи (Text-to-Speech)
│       ├── __init__.py — Пустой пакетный файл
│       └── silero_engine.py — Silero TTS движок с ленивой загрузкой (116 строк)
├── tests/ — Тестовый набор (51 тест)
│   ├── __init__.py — Пустой пакетный файл
│   ├── conftest.py — Общие фикстуры pytest (mock_protocol'ы) (96 строк)
│   ├── test_audio.py — Тесты ресемплинга, clamp и EnergyVAD (69 строк)
│   ├── test_cli.py — Тесты CLI-команд (32 строки)
│   ├── test_config.py — Тесты конфигурации (53 строки)
│   ├── test_integration.py — Интеграционные тесты полного пайплайна (170 строк)
│   ├── test_llm.py — Тесты LLM-клиента и PromptBuilder (59 строк)
│   ├── test_memory.py — Тесты ContextManager и SQLiteStore (115 строк)
│   ├── test_pipeline.py — Тесты state machine и потока диалога (116 строк)
│   ├── test_stt.py — Тесты Whisper с mock-моделью (67 строк)
│   └── test_tts.py — Тесты Silero TTS с mock-моделью (50 строк)
├── AGENTS.md — Правила работы суб-агентов и формат коммитов (39 строк)
├── DEPENDENCIES.md — Анализ зависимостей MVP и фаз масштабирования (122 строки)
├── README.md — Документация проекта: глобальные пути, команды, архитектура (70 строк)
├── .env.example — Шаблон переменных окружения (32 строки)
├── .gitignore — Правила исключения Git (194 строки)
├── pyproject.toml — Конфигурация проекта, pytest, ruff, mypy (44 строки)
├── requirements-dev.txt — Зависимости для разработки (6 строк)
└── requirements.txt — Runtime зависимости (бинарный файл)
```

## Описание компонентов

### src/core
**Путь:** `src/core/`
**Роль:** Ядро проекта — конфигурация, исключения, протоколы интерфейсов и оркестратор пайплайна.

#### Файлы
- **\_\_init\_\_.py** — Пустой пакетный файл для импорта модуля core.
- **config.py** — Конфигурация проекта на основе pydantic-settings. Класс `Config` загружает параметры из `.env` файла и переменных окружения: параметры аудио (частота, размер чанка), VAD (порог, таймауты), Whisper (модель, устройство), Ollama (URL, модель, таймаут, температура), Silero TTS (язык, голос, частота), память (путь к БД, лимит истории). Включает валидацию `vad_threshold` в диапазоне 0.0–1.0. Глобальный экземпляр `config` создаётся автоматически.
- **exceptions.py** — Иерархия исключений: `VoiceAIError` → `AudioError`/`DeviceNotFoundError`, `STTError`/`EmptyTranscriptionError`, `LLMError`/`LLMConnectionError`/`LLMTimeoutError`, `TTSError`, `MemoryError`. Позволяет перехватывать ошибки на разных уровнях абстракции.
- **pipeline.py** — Оркестратор конвейера `Pipeline` с state machine (IDLE → LISTENING → PROCESSING_STT → THINKING → SPEAKING). Dependency injection всех компонентов через конструктор. Активация по нажатию Enter, поддержка interrupt через `asyncio.Event`, graceful shutdown. Фабричный метод `create_pipeline()` собирает все компоненты автоматически.
- **protocols.py** — Protocol-интерфейсы для dependency injection: `AudioInput`, `AudioOutput`, `VAD`, `STTEngine`, `LLMClient`, `TTSEngine`, `MemoryStore`. Типы данных: `PipelineState` (enum), `Message` (TypedDict), `TurnResult`, `SessionInfo` (dataclasses).

### src/audio
**Путь:** `src/audio/`
**Роль:** Аудиоподсистема — захват и воспроизведение звука через sounddevice, а также детекция голосовой активности (VAD).

#### Файлы
- **\_\_init\_\_.py** — Пустой пакетный файл для импорта модуля audio.
- **input.py** — Класс `SoundDeviceInput`: захват аудио с микрофона через `sounddevice.InputStream` в callback-режиме (16kHz, mono, float32). Метод `record_utterance()` записывает utterance с VAD- или energy-based детекцией тишины (1.5s timeout). 使用 `asyncio.Queue` для передачи чанков.
- **output.py** — Класс `SoundDeviceOutput`: chunked-воспроизведение аудио (100ms для interrupt responsiveness) через `sd.play`. Метод `interrupt()` останавливает воспроизведение мгновенно. Утилиты: `resample_audio()` (scipy) и `clamp_audio()` для нормализации.
- **vad.py** — Класс `SileroVAD`: lazy-load модели Silero VAD через `torch.hub.load`, обработка чанков с вычислением вероятности речи. Класс `EnergyVAD`: fallback без GPU на основе RMS-энергии с порогом 0.01.

### src/stt
**Путь:** `src/stt/`
**Роль:** Распознавание речи — преобразование аудио в текст с помощью faster-whisper.

#### Файлы
- **\_\_init\_\_.py** — Пустой пакетный файл для импорта модуля stt.
- **whisper_engine.py** — Класс `FasterWhisperEngine`: lazy-load модели Whisper (large-v3 по умолчанию) через `faster_whisper.WhisperModel`. Транскрипция выполняется в отдельном потоке через `asyncio.to_thread()` с принудительным языком `ru`. Выбрасывает `EmptyTranscriptionError` при пустом результате.

### src/llm
**Путь:** `src/llm/`
**Роль:** Модуль взаимодействия с большой языковой моделью — Ollama API клиент и построение промптов.

#### Файлы
- **\_\_init\_\_.py** — Пустой пакетный файл для импорта модуля llm.
- **ollama_client.py** — Класс `OllamaClient`: асинхронный HTTP-клиент для Ollama API через `httpx`. Поддерживает стриминг (`chat_stream`, NDJSON) и синхронный (`chat`) режимы генерации. Методы `is_available()` и `list_models()` для health check. Функция `check_ollama_health()` проверяет доступность сервера и наличие нужной модели при старте.
- **prompt_builder.py** — Класс `PromptBuilder`: формирует массив сообщений для LLM из системного промпта (краткие ответы на русском, без markdown) и истории диалога. Константа `SYSTEM_PROMPT` задаёт стиль общения ассистента.

### src/tts
**Путь:** `src/tts/`
**Роль:** Синтез речи — преобразование текста в аудио через Silero TTS.

#### Файлы
- **\_\_init\_\_.py** — Пустой пакетный файл для импорта модуля tts.
- **silero_engine.py** — Класс `SileroTTSEngine`: lazy-load модели Silero TTS через `torch.hub.load` с обходом конфликта имён пакетов `src`. Синтез выполняется в отдельном потоке через `asyncio.to_thread()`. Параметры: язык `ru`, голос `baya`, частота 48kHz. Graceful degradation — возвращает `None` при ошибке (текстовый fallback).

### src/memory
**Путь:** `src/memory/`
**Роль:** Модуль памяти — хранение истории диалогов в SQLite и управление контекстом для LLM.

#### Файлы
- **\_\_init\_\_.py** — Пустой пакетный файл для импорта модуля memory.
- **context.py** — Класс `ContextManager`: обрезка истории (`trim_history`) с сохранением системного промпта, оценка токенов через эвристику (1 токен ≈ 3 символа для русского). Дублирует системный промпт из `prompt_builder.py`.
- **database.py** — Класс `SQLiteStore`: асинхронное хранение на `aiosqlite` с WAL-режимом. Таблицы `sessions` и `messages`, методы `create_session()`, `save_message()`, `get_history()` (DESC + reverse для хронологического порядка), `delete_session()`.

### src/cli
**Путь:** `src/cli/`
**Роль:** CLI-интерфейс приложения на базе Typer.

#### Файлы
- **\_\_init\_\_.py** — Пустой пакетный файл для импорта модуля cli.
- **app.py** — Typer-приложение с четырьмя командами: `run` — запуск полного голосового пайплайна с опциями модели, Whisper и устройства; `chat` — текстовый режим без микрофона; `models` — список установленных моделей Ollama; `show-config` — вывод текущей конфигурации. Настройка логирования через `logging.basicConfig`.

### src/api
**Путь:** `src/api/`
**Роль:** Зарезервировано для будущей Phase 2 — REST API и WebSocket на FastAPI.

#### Файлы
- **\_\_init\_\_.py** — Пустой пакетный файл. Модуль API пока не содержит реализаций.

### tests
**Путь:** `tests/`
**Роль:** Тестовый набор проекта — 51 тест, покрывающий все основные модули.

#### Файлы
- **\_\_init\_\_.py** — Пустой пакетный файл для импорта тестового модуля.
- **conftest.py** — Общие pytest-фикстуры: `mock_config`, `silence_chunk`, `speech_chunk`, `mock_stt`, `mock_llm`, `mock_tts`, `mock_audio_in`, `mock_audio_out`, `mock_vad`, `mock_memory`. Все mock-объекты реализуют соответствующие Protocol-интерфейсы.
- **test_config.py** — 5 тестов конфигурации: значения по умолчанию, кастомные значения, загрузка из .env, валидация vad_threshold, игнорирование лишних полей.
- **test_audio.py** — 8 тестов: ресемплинг (same/up/down rate), clamp (в пределах и за пределами), EnergyVAD (тишина, речь, диапазон вероятности).
- **test_stt.py** — 3 теста: пустое аудио → EmptyTranscriptionError, транскрипция с mock-моделью, STTError при ошибке модели.
- **test_llm.py** — 6 тестов: PromptBuilder (default/custom/empty), OllamaClient (unavailable, connection error в chat/stream, health check).
- **test_tts.py** — 3 теста: пустой текст → None, пробелы → None, синтез с mock-моделью → numpy array.
- **test_memory.py** — 12 тестов: ContextManager.trim_history (no trim, trim, no system), estimate_tokens, PromptBuilder (build, custom, empty), SQLiteStore (CRUD, limit, delete, empty).
- **test_pipeline.py** — 8 тестов: начальное состояние (IDLE, events), пустое аудио, успешный диалог, пустая транскрипция, TTS → None, shutdown.
- **test_integration.py** — 2 теста: smoke-тест полного пайплайна со stub-компонентами и проверка сохранения истории в SQLite.
- **test_cli.py** — 4 теста: show-config, models (graceful fallback), --help, run --help.

### scripts
**Путь:** `scripts/`
**Роль:** Диагностические утилиты для проверки оборудования и моделей.

#### Файлы
- **test_mic.py** — Скрипт диагностики микрофона и Silero VAD: выводит список аудиоустройств, записывает 3 секунды аудио, анализирует RMS-уровни по чанкам, тестирует Silero VAD на записанных данных. Полезен для отладки проблем со звуком.

### data
**Путь:** `data/`
**Роль:** Хранилище данных — SQLite база данных для персистентной истории диалогов.

#### Файлы
- **voice_ai.db** — База данных SQLite в формате WAL для хранения сессий и сообщений. Создаётся автоматически при первом запуске.

### reports
**Путь:** `reports/`
**Роль:** Папка для хранения отчётов и логов, генерируемых в ходе работы с проектом.

#### Файлы
- **mvp-implementation-report.md** — Детальный отчёт о реализации MVP: структура проекта, детали модулей, конфигурация, тестовое покрытие (51 тест), зависимости, бюджет задержки, следующие фазы (283 строки).
- **prompt_log.txt** — Пустой файл для логирования истории промптов. Пока не заполнен.

### reports/project-scan
**Путь:** `reports/project-scan/`
**Роль:** Папка для хранения отчётов сканирования проекта.

#### Файлы
- **report.md** — Данный отчёт сканирования.

### .vscode
**Путь:** `.vscode/`
**Роль:** Настройки VS Code для проекта.

#### Файлы
- **settings.json** — Настройка запуска pytest в VS Code: `python.testing.pytestArgs: ["tests"]`, pytest включён, unittest отключён.

### AGENTS.md
**Путь:** `AGENTS.md`
**Роль:** Корневой файл правил для суб-агентов OpenCode. Определяет обязательные практики (делегирование, тестирование, валидация, иммутабельность), запрещённые действия (утечка секретов, непроверенные изменения, дублирование), форматы агентов, навыков, хуков и стиль коммитов (conventional commits).

### README.md
**Путь:** `README.md`
**Роль:** Документация проекта: глобальные пути конфигурации OpenCode, описание команд (project-scan, prompt-analyze, architect, plan) и их взаимосвязей. Содержит схему трёхуровневой системы планирования voice_ai.

### DEPENDENCIES.md
**Путь:** `DEPENDENCIES.md`
**Роль:** Детальный анализ зависимостей MVP для Python 3.13: пошаговая установка (FastAPI, torch+CUDA, transformers, sounddevice и др.), таблица покрытия по компонентам, исключения (flask, pyaudio, kokoro), фазы масштабирования и рекомендации по безопасности.

### pyproject.toml
**Путь:** `pyproject.toml`
**Роль:** Конфигурация проекта Python: метаданные (voice_ai 0.1.0, Python ≥3.13), настройки сборки (setuptools), линтер ruff (target py313, line-length 99, правила E/F/I/N/UP/B/SIM/TCH/RUF), mypy (strict mode), pytest (testpaths, asyncio_mode=auto, marker integration).

### .env.example
**Путь:** `.env.example`
**Роль:** Шаблон переменных окружения с комментариями по секциям: Audio (SAMPLE_RATE, CHUNK_DURATION_MS, VAD_THRESHOLD), STT (WHISPER_MODEL, DEVICE, COMPUTE_TYPE), LLM (OLLAMA_BASE_URL, MODEL, TIMEOUT, TEMPERATURE, NUM_CTX), TTS (SILERO_LANGUAGE, SPEAKER), VAD (MIN_SPEECH_DURATION_MS, MIN_SILENCE_DURATION_MS, SPEECH_PAD_MS), Memory (DB_PATH, HISTORY_LIMIT), Pipeline (LOG_LEVEL).

### .gitignore
**Путь:** `.gitignore`
**Роль:** Исключения Git: стандартный Python-.gitignore + кэши (ruff, mypy, pytest) + данные БД (data/*.db*) + специфичные исключения (токены MCP, конфиги Continue).

### requirements-dev.txt
**Путь:** `requirements-dev.txt`
**Роль:** Зависимости для разработки: ipython, pytest, pytest-asyncio, pytest-cov, ruff, mypy.

### requirements.txt
**Путь:** `requirements.txt`
**Роль:** Runtime-зависимости проекта (бинарный формат, не читается напрямую). Согласно DEPENDENCIES.md включает: fastapi, uvicorn, pydantic, python-dotenv, openai, httpx, torch, transformers, sentencepiece, sounddevice, soundfile, numpy, scipy, aiosqlite, typer.

## .opencode

Конфигурационная папка OpenCode — содержит настройки агентов (архитектор, планировщик, prompt-analyst), команд (project-scan, prompt-analyze, plan, skill-create), навыков (skill-creator, voice-assistant-architect), инструкций, инструментов и TypeScript-расширений для работы ИИ-ассистента с проектом voice_ai.

---

## Сводка

- **Всего папок:** 16 (src, src/core, src/audio, src/cli, src/api, src/llm, src/memory, src/stt, src/tts, tests, scripts, data, reports, reports/project-scan, .vscode, .opencode)
- **Всего файлов:** 43 (без учёта содержимого `.opencode/` и исключённых директорий `__pycache__`, `.venv`, `.pytest_cache`, `.ruff_cache`, `.git`)
- **Основной язык:** Python 3.13
- **Ключевые технологии:** Python (asyncio, pydantic-settings, Protocol), faster-whisper (STT), Silero (VAD + TTS), Ollama/qwen2.5 (LLM), sounddevice (аудио I/O), aiosqlite (память), httpx (HTTP-клиент), Typer (CLI), scipy (ресемплинг), pytest (тестирование), ruff + mypy (линтинг и типизация)