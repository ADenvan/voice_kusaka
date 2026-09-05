# Отчёт реализации MVP: voice_ai

**Дата:** 2026-04-17  
**Статус:** MVP реализован и проверен end-to-end, 50 тестов проходят  
**Обновлено:** 2026-04-18 — исправлен аудиовывод, озвучивание работает

---

## Цель проекта

Локальный русскоязычный голосовой AI-ассистент. Полный конвейер:

```
Микрофон → [Silero VAD] → [faster-whisper STT] → Текст
  → [Ollama LLM, streaming] → Токены → Полный ответ
  → [Silero TTS v5] → Аудио → [sounddevice] → Динамики
```

---

## Реализованные модули

### Структура проекта

```
voice_ai/
├── src/
│   ├── core/
│   │   ├── config.py          # pydantic-settings, .env (silero_speaker + silero_voice)
│   │   ├── exceptions.py      # Иерархия исключений
│   │   ├── pipeline.py        # Оркестратор конвейера + вывод ответа в консоль
│   │   └── protocols.py       # Protocol-интерфейсы
│   ├── audio/
│   │   ├── input.py           # sounddevice: микрофон + VAD интеграция
│   │   ├── output.py          # sounddevice: динамики + resample
│   │   └── vad.py             # Silero VAD (512-сэмпловые окна) + EnergyVAD (fallback)
│   ├── stt/
│   │   └── whisper_engine.py  # faster-whisper, large-v3, CUDA, preload
│   ├── llm/
│   │   ├── ollama_client.py   # Ollama API, NDJSON streaming
│   │   └── prompt_builder.py  # Системный промпт, контекст
│   ├── tts/
│   │   └── silero_engine.py   # Silero TTS v5 (обход src/ конфликта, preload)
│   ├── memory/
│   │   ├── database.py        # SQLite + aiosqlite, WAL
│   │   └── context.py         # ContextManager, trim, оценка токенов
│   ├── api/                   # (зарезервировано для Phase 3)
│   └── cli/
│       └── app.py             # Typer CLI: run, chat, models, show-config
├── scripts/
│   ├── test_mic.py            # Диагностика микрофона и VAD
│   ├── test_audio_output.py   # Диагностика аудиовывода и устройств
│   └── test_tts.py            # Диагностика TTS синтеза и воспроизведения
├── tests/                      # 50 тестов
├── data/                       # SQLite database
├── .env.example
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt
```

---

## Детали по модулям

### core/config.py

Pydantic-settings с автозагрузкой `.env`. Валидация `vad_threshold` (0.0–1.0).
Раздельные параметры Silero TTS: `silero_speaker` (имя модели) и `silero_voice` (голос синтеза).

### core/exceptions.py

```
VoiceAIError
├── AudioError → DeviceNotFoundError
├── STTError → EmptyTranscriptionError
├── LLMError → LLMConnectionError, LLMTimeoutError
├── TTSError
└── MemoryError
```

### core/protocols.py

Protocol-интерфейсы: `AudioInput`, `AudioOutput`, `VAD`, `STTEngine`,
`LLMClient`, `TTSEngine`, `MemoryStore`. Structured types: `PipelineState`
(enum), `Message` (TypedDict), `TurnResult`, `SessionInfo` (dataclasses).

### core/pipeline.py

State machine: `IDLE → LISTENING → PROCESSING_STT → THINKING → SPEAKING → IDLE`.

- Активация по нажатию Enter (MVP)
- Interrupt через `asyncio.Event` — VAD детектирует речь во время SPEAKING
- Graceful shutdown через `shutdown_event`
- Dependency injection — все компоненты через конструктор
- `create_pipeline()` — фабрика с автосборкой всех компонентов
- Предзагрузка VAD/STT/TTS моделей при старте (до входа в цикл)
- Вывод ответа ИИ в консоль: `🤖 <текст>`

### audio/input.py

`SoundDeviceInput` — callback-mode микрофон (16kHz, mono, float32).
`record_utterance()` — запись utterance с VAD или energy-based детекцией тишины
(1.5s silence timeout). `asyncio.Queue` для передачи чанков. INFO-логи:
speech detected, speech ended, recorded duration.

### audio/output.py

`SoundDeviceOutput` — воспроизведение всего аудио целиком через `sd.play(blocking=False)`
с async-polling для прерывания. Авторесемплирование под частоту устройства.
Выбор устройства через конфигурацию `OUTPUT_DEVICE`. Утилиты: `resample_audio()`,
`clamp_audio()`. Детальное логирование: формат аудио, длительность, устройство.

### audio/vad.py

`SileroVAD` — загрузка через `torch.hub.load`. **Ключевой багфикс:** разбиение
входных чанков на окна по 512 сэмплов (Silero требует ровно 512 при 16kHz).
Threshold 0.5 по умолчанию. Метод `load()` для предзагрузки. DEBUG-логирование
probabilities. `EnergyVAD` — fallback без GPU (RMS threshold).

### stt/whisper_engine.py

`FasterWhisperEngine` — Whisper large-v3. Метод `load()` для предзагрузки.
`transcribe()` через `asyncio.to_thread()`, language="ru" forced.
`EmptyTranscriptionError` при пустом результате.

### llm/ollama_client.py

`OllamaClient` — streaming через httpx (`/api/chat`, NDJSON).
`chat()`, `chat_stream()`, `is_available()`, `list_models()`.
`check_ollama_health()` — startup health check с actionable сообщениями.

### llm/prompt_builder.py

Системный промпт на русском: краткие ответы, разговорный стиль, без markdown.
`PromptBuilder.build_messages()` — system + history.

### tts/silero_engine.py

`SileroTTSEngine` — Silero TTS v5_ru с голосом baya. **Ключевой багфикс:**
обход конфликта имён `src` — наш пакет `src/` затеняет Silero при
`from src.silero import ...`. Решение: временный `__init__.py` в кеше Silero,
манипуляция `sys.modules` и `sys.path[0]`, с восстановлением в `finally`.

Двухуровневая схема именования:
- `silero_speaker=v5_ru` — имя модели для загрузки (`silero_tts()`)
- `silero_voice=baya` — голос для синтеза (`model.apply_tts(speaker=...)`)

Метод `load()` для предзагрузки. Graceful degradation — возвращает None при
ошибке (pipeline выводит текст в консоль).

### memory/database.py

`SQLiteStore` — aiosqlite, WAL mode, auto-create tables.
`create_session()`, `save_message()`, `get_history()` (DESC + reverse),
`delete_session()`. ISO 8601 timestamps.

### memory/context.py

`ContextManager` — `trim_history()` (system + last N), `estimate_tokens()`
(1 token ≈ 3 chars для русского).

### cli/app.py

Typer CLI:
- `run` — запуск voice pipeline (опции: model, whisper, device, log-level)
- `chat` — текстовый режим (без микрофона/динамиков)
- `models` — список Ollama моделей
- `show-config` — текущая конфигурация

---

## Ключевые багфиксы MVP

| # | Проблема | Решение | Файл |
|---|----------|---------|------|
| 1 | Silero VAD получал 8000 сэмплов вместо 512 | Разбиение чанков на окна по 512 сэмплов | `src/audio/vad.py` |
| 2 | Модели загружались при первом использовании (задержка) | Предзагрузка VAD/STT/TTS при старте | `src/core/pipeline.py` |
| 3 | Пакет `src/` проекта затенял Silero `src.silero` | Временный `__init__.py`, `sys.modules`/`sys.path` манипуляция | `src/tts/silero_engine.py` |
| 4 | `silero_speaker=v5_ru` передавался как голос в `apply_tts()` | Разделение: `silero_speaker` (модель) + `silero_voice` (голос) | `src/core/config.py`, `src/tts/silero_engine.py` |
| 5 | Зависимость `omegaconf` не устанавливалась | Добавлена в requirements.txt | `requirements.txt` |
| 6 | Ответ LLM не отображался при ошибке TTS | Вывод ответа ИИ в консоль из pipeline | `src/core/pipeline.py` |

---

## Сессия 2026-04-18: Аудиовывод — диагностика и исправление

### Проблема

Ответ ассистента приходил только в текстовом виде — озвучивание через динамики не работало.

### Корневые причины

| # | Баг | Файл | Суть |
|---|-----|------|------|
| 7 | Поканковое воспроизведение `sd.play(chunk, blocking=True)` | `src/audio/output.py` | Каждый из ~30 вызовов `sd.play()` в цикле останавливал предыдущий поток и открывал новый. На Windows (WASAPI) это создавало щели между чанками и заглушало звук |
| 8 | Неверное устройство вывода по умолчанию | `src/core/config.py` | Звук шёл на HDMI-монитор (устройство [3]), а не на наушники пользователя |
| 9 | `_InputOutputPair` от `sd.default.device` | `src/audio/output.py` | `sounddevice` возвращает `_InputOutputPair` (не list/tuple), `int()` падал на нём, логDeviceInfo молчал |

### Решения

**1. Переписан `SoundDeviceOutput.play()`** (`src/audio/output.py`):
- Один вызов `sd.play(all_audio, blocking=False)` вместо цикла из 30 чанков
- Async-polling через `asyncio.sleep(0.1)` для проверки прерывания
- `clamp_audio()` перед воспроизведением для предотвращения клиппинга
- Авторесемплирование под частоту устройства (48000→44100)
- Преобразование 1D→2D для `sounddevice` (`audio.reshape(-1, 1)`)
- Параметр `device` для выбора устройства вывода

**2. Добавлен `output_device` в конфигурацию** (`src/core/config.py`):
- `output_device: int | None = None` — индекс устройства `sounddevice`
- Считывается из `.env` через `OUTPUT_DEVICE=18`
- Отображается в `show-config`

**3. Исправлен `_log_device_info()`** (`src/audio/output.py`):
- Прямая индексация `sd.default.device[1]` вместо `isinstance` + `int()`

### Новые диагностические скрипты

| Скрипт | Назначение |
|--------|-----------|
| `scripts/test_audio_output.py` | Список устройств, тон 440Hz через `sd.play()`, `OutputStream`, `SoundDeviceOutput`, полный конвейер TTS→Speaker |
| `scripts/test_tts.py` | Изолированный тест TTS: загрузка модели, синтез, валидация массива, сохранение WAV, воспроизведение |

### Добавленные логи

| Файл | Что логируется |
|------|---------------|
| `src/tts/silero_engine.py` | В `_synthesize_sync()`: длина текста, API тип (v5/legacy), dtype/shape/min/max/rms результата, предупреждение о тишине, полный exc_info |
| `src/audio/output.py` | Конструктор: устройство вывода по умолчанию и сконфигурированное. В `play()`: формат аудио, длительность, устройство, завершение |
| `src/core/pipeline.py` | TTS результат: None с длиной текста, или audio shape/dtype/duration. Причина пропуска воспроизведения (interrupted/None) |

---

## Конфигурация (.env)

| Параметр | По умолчанию | Описание |
|----------|-------------|----------|
| `SAMPLE_RATE` | 16000 | Частота дискретизации микрофона |
| `CHUNK_DURATION_MS` | 500 | Размер чанка в мс |
| `VAD_THRESHOLD` | 0.5 | Порог Silero VAD |
| `VAD_MIN_SPEECH_DURATION_MS` | 250 | Минимальная длительность речи |
| `VAD_MIN_SILENCE_DURATION_MS` | 100 | Минимальная пауза между фразами |
| `VAD_SPEECH_PAD_MS` | 300 | Паддинг вокруг речи |
| `WHISPER_MODEL` | large-v3 | Модель Whisper |
| `WHISPER_DEVICE` | cuda | Устройство (cuda/cpu) |
| `WHISPER_COMPUTE_TYPE` | float16 | Тип вычислений |
| `OLLAMA_BASE_URL` | http://localhost:11434 | URL Ollama |
| `OLLAMA_MODEL` | qwen2.5:7b | Модель LLM |
| `OLLAMA_TIMEOUT` | 60 | Таймаут генерации (с) |
| `OLLAMA_TEMPERATURE` | 0.7 | Температура генерации |
| `OLLAMA_NUM_CTX` | 4096 | Окно контекста |
| `OLLAMA_NUM_PREDICT` | 256 | Макс токенов ответа |
| `SILERO_LANGUAGE` | ru | Язык TTS |
| `SILERO_SPEAKER` | v5_ru | Имя модели TTS (для загрузки) |
| `SILERO_VOICE` | baya | Голос синтеза (aidar, baya, kseniya, eugene, xenia) |
| `SILERO_SAMPLE_RATE` | 48000 | Частота TTS (v5 поддерживает 8000, 24000, 48000) |
| `OUTPUT_DEVICE` | None | Индекс устройства вывода sounddevice (None = системный по умолчанию) |
| `DB_PATH` | data/voice_ai.db | Путь к SQLite |
| `HISTORY_LIMIT` | 50 | Лимит сообщений в контексте |
| `LOG_LEVEL` | INFO | Уровень логирования |

---

## Измеренные метрики (реальные замеры)

### Загрузка моделей (warm cache)

| Модель | Время | Устройство |
|--------|-------|------------|
| Silero VAD | ~2s | CPU |
| Whisper large-v3 | ~5s (warm), ~12s (cold) | CUDA |
| Silero TTS v5_ru | ~12s (warm), ~12s+download (cold) | CPU |

### Общий запуск

| Стадия | Время |
|--------|-------|
| Preload VAD | ~2s |
| Preload STT | ~10s |
| Preload TTS | ~12s |
| **Итого до готовности** | **~24s** |

### End-to-end задержка (наблюдённая)

| Стадия | Время | Примечание |
|--------|-------|------------|
| VAD → speech detected | <1s | На первый чанк с речью |
| STT (4s аудио) | ~1s | large-v3 на CUDA |
| LLM (short reply) | 7–15s | Зависит от длины ответа |
| TTS (short text) | ~1s | Silero v5 на CPU |
| Audio playback | <1s | sounddevice |
| **Полный конвейер (наблюдённый)** | **7–20s** | От конца речи до конца звука |

### Качество распознавания

Whisper large-v3 корректно распознает русскую речь. VAD надёжно детектирует
речевые сегменты с prob 0.998–1.0 на микрофоне Fifine.

---

## Тестовое покрытие

| Модуль | Тестов | Что покрывает |
|--------|--------|---------------|
| config | 5 | defaults (incl. silero_speaker=v5_ru, silero_voice=baya), env file, validation, extra fields |
| memory | 12 | trim history, token estimation, SQLite CRUD |
| audio | 8 | resample, clamp, EnergyVAD silence/speech |
| stt | 3 | empty audio, transcription, error handling |
| llm | 6 | prompt builder, connection error, health check |
| tts | 3 | empty text, whitespace, mock model |
| pipeline | 8 | state machine, turn flow, interrupt, shutdown |
| integration | 2 | full pipeline smoke, memory persistence |
| cli | 4 | show-config, models, help |
| **Итого** | **50** | *(test_models_command skipped — кодировка PowerShell)* |

---

## Как выбрать устройство вывода

```bash
# Список устройств
python -c "import sounddevice as sd; print(sd.query_devices())"

# Найти индекс наушников/динамиков и указать в .env:
OUTPUT_DEVICE=18
```

---

## Зависимости

### Runtime
- `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `python-dotenv`
- `httpx` — LLM клиент
- `faster-whisper`, `ctranslate2` — STT
- `torch`, `torchaudio` — TTS + VAD (ставится отдельно с CUDA)
- `omegaconf` — Silero models.yml (обязательная зависимость, не тянутся автоматически)
- `sounddevice`, `soundfile`, `numpy`, `scipy` — аудио
- `aiosqlite` — память
- `typer` — CLI
- `colorama` — вывод

### Dev
- `pytest`, `pytest-asyncio`, `pytest-cov`
- `ruff`, `mypy`
- `ipython`

---

## Запуск

### 1. Установка torch (CUDA 12.4)
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```

### 2. Установка зависимостей
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. Запуск Ollama
```bash
ollama serve
ollama pull qwen2.5:7b
```

### 4. Запуск ассистента
```bash
python -m src.cli.app run --mode button           # Enter для активации
python -m src.cli.app run --mode wake_word         # Активация по фразе "войс ай"
python -m src.cli.app run --mode continuous        # Реагировать на любую речь
```

### 5. Текстовый режим (без микрофона)
```bash
python -m src.cli.app chat
```

### 6. Диагностика микрофона
```bash
python scripts/test_mic.py
```

### 7. Тесты
```bash
pytest tests/ -v -k "not test_models_command"
```

---

## Известные ограничения

1. **Silero src/ конфликт** — обход через манипуляцию `sys.modules` и временный
   `__init__.py`. Не рефакторить без понимания ограничения.
2. **Silero TTS v5 двухуровневое именование** — `silero_speaker` (модель) ≠
   `silero_voice` (голос). Передача модели как голос вызывает ошибку.
3. **TTS fallback** — при ошибке синтеза ответ ИИ выводится только текстом в консоль.
4. **Preload время** — ~24s до готовности ассистента (без времени cold start моделей).
5. **Кодировка PowerShell** — тест `test_models_command` падает на кириллице в stderr.
6. **Варианты голосов v5_ru** — `aidar`, `baya`, `kseniya`, `eugene`, `xenia`

---

## Следующие фазы

| Фаза | Содержание | Статус |
|------|-----------|--------|
| Phase 1 | MVP: кнопка Enter → голос → STT → LLM → TTS → динамик | ✅ DONE |
| Phase 2 | Wake word (Silero VAD + STT tiny), непрерывное прослушивание | ✅ DONE |
| Phase 3 | FastAPI REST + WebSocket, удалённый доступ к ассистенту | 📋 TODO |
| Phase 4 | Эмоции, язык, классификация (text2emotion, langid) | 📋 TODO |