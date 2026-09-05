# Анализ зависимостей проекта voice_ia

## MVP-набор для Python 3.13

**Полный цикл:** Микрофон → STT → LLM → TTS → Динамики + API

### Команды установки

```bash
# Шаг 1: API-сервер + LLM + утилиты
pip install fastapi uvicorn pydantic python-dotenv openai httpx

# Шаг 2: ML-фреймворк (CUDA 12.4)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# Шаг 3: Модели STT/TTS
pip install transformers sentencepiece

# Шаг 4: Аудио-обработка
pip install soundfile numpy scipy

# Шаг 5: Утилиты
pip install requests tqdm colorama
```

Или одной строкой (без torch):
```bash
pip install fastapi uvicorn pydantic python-dotenv openai httpx transformers sentencepiece soundfile numpy scipy requests tqdm colorama
```

> **Важно:** `torch` ставится отдельно с указанием index-url для CUDA. На Python 3.13 может не быть готовых wheels — если упадёт, используй `--pre` флаг или nightly-билд.

### Что покрывает MVP

| Компонент | Пакеты |
|-----------|--------|
| API-сервер | `fastapi`, `uvicorn`, `pydantic`, `python-dotenv` |
| LLM (облако) | `openai`, `httpx` |
| STT/TTS/Модели | `torch`, `transformers`, `sentencepiece` |
| Аудио-обработка | `soundfile`, `numpy`, `scipy` |
| Утилиты | `requests`, `tqdm`, `colorama` |

### Что НЕ включено (и почему)

| Исключено | Причина |
|-----------|---------|
| `flask` | Конфликтует с FastAPI — для MVP достаточно одного фреймворка |
| `ollama`, `together` | `openai`-клиент поддерживает совместимые API (Ollama через `base_url`) |
| `pyaudio` | Сложная компиляция на Python 3.13 / Windows — отложить до необходимости |
| `librosa` | Тяжёлый; `scipy` + `soundfile` покрывают базовый аудио MVP |
| `celery` | Очередь задач — не нужна на старте |
| `pydantic_core`, `certifi`, `anyio`, `sniffio`, `jiter`, `distro` | Транзитивные зависимости — подтянутся автоматически |
| `selenium` + stealth-стек | Не ядро голосового ассистента |
| `text2emotion`, `langid`, `adaptive-classifier` | Вспомогательные — добавить позже |
| `ipython`, `setuptools` | Dev-инструменты, не runtime |
| `kokoro` | Требует Python <3.12, несовместим |

---

## Масштабирование по фазам

### Фаза 2 — Локальный LLM
```bash
pip install ollama
```
> **Совет:** `openai`-клиент может работать с Ollama через `base_url="http://localhost:11434/v1"` — отдельный пакет нужен только если используешь Ollama SDK напрямую

### Фаза 3 — Продвинутое аудио
```bash
pip install librosa pyaudio playsound3
```
> **Совет:** `pyaudio` на Windows ставится через `pip install pipwin && pipwin install pyaudio`. На Python 3.13 может не собираться — рассмотри `sounddevice` как альтернативу

### Фаза 4 — Эмоции, язык, классификация
```bash
pip install text2emotion langid adaptive-classifier sacremoses
```

### Фаза 5 — Веб-скрапинг (если нужен)
```bash
pip install selenium undetected-chromedriver fake_useragent markdownify
```

### Фаза 6 — Фоновые задачи
```bash
pip install celery aiofiles
```

---

## Рекомендации

### Структура зависимостей
- Раздели на `requirements.txt` (runtime) и `requirements-dev.txt` (ipython, pytest и т.д.)
- Убери транзитивные зависимости — они подтянутся автоматически
- Используй `pip freeze > requirements.lock` для фиксации точных версий в продакшене
- Рассмотри `uv` вместо `pip` — в 10-100 раз быстрее

### Выбор фреймворка
- Выбери **FastAPI** — async native, идеально для real-time аудио и WebSocket
- Flask оставь только если есть веская причина (существующий код, синхронные зависимости)

### Python 3.13 совместимость
- `torch` — может понадобиться `--pre` флаг или nightly-билд
- `pyaudio` — сложная компиляция, рассмотри `sounddevice` или `pyttsx3`
- `librosa` — обычно OK, но проверь совместимость зависимостей
- `kokoro` —**не совместим**, требует <3.12

### Безопасность
- Не храни API-ключи в коде — используй `.env` + `python-dotenv`
- Добавь `.env` в `.gitignore`
- Фиксируй верхние границы версий для production: `fastapi>=0.115.12,<1`

### Аудио на MVP
- Для записи с микрофона на MVP достаточно `sounddevice` + `soundfile` (легче чем pyaudio)
- Для TTS на старте используй OpenAI API (`openai` клиент) — не нужен локальный TTS
- Для STT тоже можно через OpenAI Whisper API — без установки тяжёлых моделей локально



