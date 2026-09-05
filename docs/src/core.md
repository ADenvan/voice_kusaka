# Документация модуля Core

## Обзор

Папка `src/core` — это **фундаментальный слой** приложения voice_ai. Она содержит:

- **Конфигурацию** — единый объект `Config`, используемый всеми модулями
- **Контракты** — интерфейсы (Protocol) для всех подсистем
- **Иерархию ошибок** — доменные исключения
- **Оркестратор** — `Pipeline`, который собирает все подсистемы и управляет диалогом

Модуль находится во **внутреннем слое** архитектуры — от него зависят все остальные модули проекта.

---

## Структура файлов

```
src/core/
├── __init__.py      # Пустой маркер пакета
├── config.py        # Конфигурация приложения (pydantic-settings)
├── exceptions.py    # Иерархия исключений
├── protocols.py     # Интерфейсы (Protocol) и типы данных
└── pipeline.py      # Оркестратор + фабрика
```

---

## Файлы

### `config.py`

Централизованная конфигурация на базе `pydantic-settings`. Загружает значения из `.env` и переменных окружения.

**Основные настройки:**
- Аудио: `sample_rate`, `chunk_duration_ms`
- VAD: `vad_threshold`, `vad_min_speech_duration_ms`, `vad_min_silence_duration_ms`
- STT: `whisper_model`, `whisper_device`, `whisper_compute_type`
- LLM: `ollama_url`, `ollama_model`, `ollama_timeout`, `ollama_temperature`, `ollama_context_window`
- TTS: `silero_language`, `silero_speaker`, `silero_voice`, `silero_sample_rate`
- Режимы: `activation_mode` (`button`, `wake_word`, `continuous`)
- Wake-word: `wake_word_model`, `wake_word_phrases`, `wake_word_cooldown`
- Память: `db_path`, `history_limit`

**Экспорт:** `Config` (класс), `config` (синглтон).

---

### `exceptions.py`

Иерархия доменных исключений. Все наследуются от `VoiceAIError`.

```
VoiceAIError (базовое)
├── AudioError
│   └── DeviceNotFoundError
├── STTError
│   └── EmptyTranscriptionError
├── LLMError
│   ├── LLMConnectionError
│   └── LLMTimeoutError
├── TTSError
├── WakeWordError
└── MemoryError
```

**Экспорт:** 10 классов исключений.

---

### `protocols.py`

Слой контрактов — определяет интерфейсы через Python `Protocol`, отделяя оркестратор от конкретных реализаций.

**Типы данных:**
- `PipelineState` — Enum состояний: `IDLE`, `LISTENING`, `PROCESSING_STT`, `THINKING`, `SPEAKING`
- `Message` — TypedDict с `role`, `content`, `timestamp`
- `TurnResult` — результат одного оборота диалога (текст пользователя, ответ, задержка, прерывание)
- `SessionInfo` — метаданные сессии

**Интерфейсы (Protocol):**
- `AudioInput` — `start()`, `stop()`, `read_chunk()`
- `AudioOutput` — `play()`, `interrupt()`, `stop()`
- `VAD` — `is_speech()`, `get_speech_prob()`
- `STTEngine` — `transcribe()`
- `LLMClient` — `chat_stream()`, `chat()`
- `TTSEngine` — `synthesize()`
- `WakeWordDetector` — `load()`, `detect()`
- `MemoryStore` — `save_message()`, `get_history()`, `create_session()`, `delete_session()`

**Экспорт:** `PipelineState`, `Message`, `TurnResult`, `SessionInfo`, 8 Protocol-классов.

---

### `pipeline.py`

Центральный оркестратор — связывает все подсистемы и управляет циклом диалога. Самый сложный файл в `core`.

**Класс `Pipeline`:**
- Принимает все зависимости через конструктор (Dependency Injection)
- Управляет состоянием через `PipelineState`
- Координирует завершение через `asyncio.Event`
- Поддерживает два режима: `_run_button_mode()` и `_run_continuous_mode()`

**Основной цикл оборота (`_process_audio`):**
1. STT-транскрипция
2. Сохранение сообщения пользователя в память
3. Построение промпта с историей
4. Стриминг ответа LLM (с проверкой прерываний)
5. Сохранение ответа ассистента
6. TTS-синтез
7. Воспроизведение аудио
8. Возврат `TurnResult`

**Фабрика `create_pipeline`:**
Создаёт все конкретные реализации из `Config` и возвращает готовый `Pipeline`. Это точка сборки зависимостей.

**Экспорт:** `Pipeline` (класс), `create_pipeline` (фабрика).

---

## Зависимости

### Внутренние зависимости (внутри `src/core`)

```
config.py ──────────┐
exceptions.py ──────┼────► pipeline.py
protocols.py ───────┘
```

`pipeline.py` — единственный потребитель остальных трёх модулей внутри `core`. Остальные три файла независимы друг от друга.

### Исходящие зависимости (что импортирует `src/core`)

Только `pipeline.py` импортирует конкретные реализации из других модулей:

| Откуда | Что импортирует |
|--------|-----------------|
| `src.audio.input` | `SoundDeviceInput` |
| `src.audio.output` | `SoundDeviceOutput` |
| `src.audio.vad` | `SileroVAD` |
| `src.audio.wake_word` | `STTWakeWord` |
| `src.llm.ollama_client` | `OllamaClient` |
| `src.llm.prompt_builder` | `PromptBuilder` |
| `src.memory.context` | `ContextManager` |
| `src.memory.database` | `SQLiteStore` |
| `src.stt.whisper_engine` | `FasterWhisperEngine` |
| `src.tts.silero_engine` | `SileroTTSEngine` |

### Входящие зависимости (кто зависит от `src/core`)

**Все модули проекта** зависят от `src.core`:

- `src.cli` — `Config`, `create_pipeline`
- `src.audio` — `Config`, `DeviceNotFoundError`, `WakeWordError`
- `src.stt` — `Config`, `STTError`, `EmptyTranscriptionError`
- `src.llm` — `Config`, `LLMConnectionError`, `LLMTimeoutError`
- `src.tts` — `Config`
- `src.memory` — `Config`, `MemoryError`
- `tests/*` — `Config`, `Pipeline`, `PipelineState`, исключения

`Config` — самый широко используемый символ, импортируется практически каждым модулем.

---

## Архитектурные паттерны

### Dependency Injection

Все 8 подсистем инжектируются в `Pipeline` через конструктор. Класс никогда не создаёт конкретные реализации сам.

### Factory Function

`create_pipeline()` — единственная фабрика, которая собирает все конкретные классы из `Config`. Это точка композиции.

### Protocol / Structural Typing

Python `Protocol` определяет duck-typed контракты. Конкретные классы в `src.audio`, `src.stt` и т.д. удовлетворяют протоколам неявно.

### State Machine

`PipelineState` + `Pipeline.state` отслеживает текущую фазу: `IDLE → LISTENING → PROCESSING_STT → THINKING → SPEAKING → IDLE`.

### Async Event Coordination

`interrupt_event` и `shutdown_event` (`asyncio.Event`) координируют корректное завершение и прерывание пользователя между конкурентными задачами.

### Strategy Pattern

Режимы активации (`_run_button_mode` vs `_run_continuous_mode`) выбираются в рантайме на основе `config.activation_mode`.

### Singleton Configuration

Модульный синглтон `config = Config()` экспортируется для удобства, но `Config` также можно инстанцировать с переопределениями (как делает `cli/app.py`).

---

## Поток данных

```
Пользователь говорит
    │
    ▼
AudioInput ──► VAD ──► WakeWordDetector (опционально)
    │
    ▼
STTEngine.transcribe() ──► текст
    │
    ▼
MemoryStore.save_message(пользователь)
    │
    ▼
PromptBuilder.build_messages(history)
    │
    ▼
LLMClient.chat_stream(messages) ──► стрим токенов
    │
    ▼
MemoryStore.save_message(ассистент)
    │
    ▼
TTSEngine.synthesize(response) ──► аудио
    │
    ▼
AudioOutput.play(audio)
    │
    ▼
Пользователь слышит ответ
```

---

## Итог

`src/core` — это **хребет** приложения. Она не содержит циркулярных зависимостей внутри себя, зависит наружу от конкретных реализаций подсистем (только в `pipeline.py`), и от неё зависит каждый другой модуль проекта для конфигурации, контрактов и типов ошибок.
