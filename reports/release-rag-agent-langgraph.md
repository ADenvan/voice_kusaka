# Release Report: LangGraph RAG Agent

**Дата релиза:** 2026-09-10  
**Версия:** 0.3.0  
**Автор:** AI Assistant (opencode)  
**Контекст:** Интеграция RAG агента с LangGraph, ChromaDB и DuckDuckGo

---

## 1. Схемы изменений

### Дерево затронутых файлов

```
voice_kusaka/
├── requirements.txt                    # + 8 зависимостей (langgraph, chromadb, etc.)
├── pyproject.toml                      # mypy overrides для новых библиотек
├── .env.example                        # + блок RAG настроек (11 полей)
│
├── data/
│   └── pdf/                            # НОВАЯ директория для PDF документов
│
├── src/
│   ├── rag/                            # НОВЫЙ модуль (9 файлов)
│   │   ├── __init__.py                 # Экспорт RAGClient
│   │   ├── config.py                   # RAGConfig (pydantic model)
│   │   ├── embeddings.py               # EmbeddingProvider (HuggingFace)
│   │   ├── pdf_loader.py               # PDFDocumentLoader (pypdf + chunking)
│   │   ├── vectorstore.py              # ChromaVectorStore (ChromaDB wrapper)
│   │   ├── web_search.py               # DuckDuckGoSearchTool
│   │   ├── prompts.py                  # Промпты для графа (router, graders)
│   │   ├── graph.py                    # LangGraph StateGraph builder
│   │   └── agent.py                    # RAGClient (реализует LLMClient)
│   │
│   ├── core/
│   │   ├── config.py                   # + 11 RAG полей конфигурации
│   │   └── pipeline.py                 # + автоактивация RAG при наличии PDF
│   │
│   └── cli/
│       └── app.py                      # + 4 команды: rag-scan, rag-query, rag-stats, rag-clear
│
└── tests/
    └── test_rag/                       # НОВЫЙ (5 файлов)
        ├── __init__.py
        ├── test_config.py              # Тесты RAGConfig
        ├── test_graph.py               # Тесты графа (JSON parsing, format_docs)
        ├── test_pdf_loader.py          # Тесты загрузки PDF
        └── test_vectorstore.py         # Тесты ChromaDB wrapper
```

### Архитектурная схема RAG агента

```
┌─────────────────────────────────────────────────────────────┐
│                    User Query                                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    RAGClient (LLMClient protocol)            │
│  - chat(messages) → str                                     │
│  - chat_stream(messages) → AsyncIterator[str]               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph StateGraph                      │
│                                                              │
│  ┌──────────┐    ┌─────────────┐    ┌──────────────┐       │
│  │  Router  │───▶│ VectorStore │───▶│ Grade Docs   │       │
│  │(LLM JSON)│    │  Retrieve   │    │ (LLM JSON)   │       │
│  └──────────┘    └─────────────┘    └──────────────┘       │
│       │                                      │               │
│       │ websearch                            │ not relevant  │
│       ▼                                      ▼               │
│  ┌──────────┐                         ┌──────────┐          │
│  │   Web    │◄────────────────────────│   Web    │          │
│  │  Search  │                         │  Search  │          │
│  │(DuckDuck)│                         │(DuckDuck)│          │
│  └──────────┘                         └──────────┘          │
│       │                                      │               │
│       └──────────────┬───────────────────────┘               │
│                      ▼                                       │
│               ┌──────────┐                                   │
│               │ Generate │ ← LLM генерирует ответ            │
│               └──────────┘                                   │
│                      │                                       │
│                      ▼                                       │
│               ┌──────────┐                                   │
│               │  Grader  │ ← Проверка галлюцинаций           │
│               │(LLM JSON)│   + проверка ответа на вопрос     │
│               └──────────┘                                   │
│                      │                                       │
│             ┌────────┴────────┐                              │
│             │                 │                              │
│          useful          not useful                          │
│             │                 │                              │
│             ▼                 ▼                              │
│          ┌─────┐          ┌──────┐                           │
│          │ END │          │Retry │ (до max_retries)          │
│          └─────┘          └──────┘                           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Response to User                          │
└─────────────────────────────────────────────────────────────┘
```

### CLI команды

```bash
# Сканировать PDF директорию и обновить vectorstore
python -m src.cli.app rag-scan [--directory data/pdf]

# Запрос к RAG агенту (текстовый режим)
python -m src.cli.app rag-query "Вопрос?"

# Показать статистику vectorstore
python -m src.cli.app rag-stats

# Очистить vectorstore
python -m src.cli.app rag-clear

# Показать конфигурацию (включая RAG настройки)
python -m src.cli.app show-config
```

---

## 2. Статус и описание работы

### Краткая суть

Реализован полноценный RAG (Retrieval-Augmented Generation) агент на базе LangGraph с интеграцией ChromaDB для векторного хранилища и DuckDuckGo для веб-поиска.

**Ключевые возможности:**
- **Автоактивация RAG** — если в `data/pdf/` есть PDF файлы, pipeline автоматически использует RAG agent вместо обычного LLM client
- **Маршрутизация запросов** — LLM решает, использовать vectorstore или web search
- **Проверка релевантности** — каждый документ оценивается на релевантность вопросу
- **Проверка галлюцинаций** — ответ проверяется на соответствие документам
- **Проверка качества ответа** — ответ проверяется на соответствие вопросу
- **Retry логика** — до 3 попыток генерации (настраивается)
- **PDF загрузка** — рекурсивная загрузка PDF из директории с чанкингом
- **ChromaDB persistence** — vectorstore сохраняется между запусками
- **DuckDuckGo** — бесплатный веб-поиск без API ключа

**Реализовано:**
- Полный LangGraph state machine с 4 узлами (retrieve, grade_documents, generate, web_search)
- RAGClient реализует протокол `LLMClient` для бесшовной интеграции в pipeline
- 11 полей конфигурации в `Config` для настройки RAG
- 4 CLI команды для управления RAG
- 18 unit тестов для RAG модулей
- Интеграция с существующими LLM провайдерами (Ollama, LM Studio)

**Не реализовано / заглушки:**
- Streaming для RAG — `chat_stream()` возвращает полный ответ одним чанком (для совместимости с TTS)
- Автоопределение темы для router — используется общий промпт без специфичной темы
- UI для управления RAG — только CLI
- Fallback между провайдерами при недоступности

---

### Статусы задач

| # | Задача | Статус |
|---|--------|--------|
| 1 | Установить зависимости (langgraph, chromadb, pypdf, duckduckgo-search, langchain-huggingface) | [Сделано] |
| 2 | Создать `src/rag/config.py` — RAGConfig | [Сделано] |
| 3 | Создать `src/rag/embeddings.py` — EmbeddingProvider | [Сделано] |
| 4 | Создать `src/rag/pdf_loader.py` — PDFDocumentLoader | [Сделано] |
| 5 | Создать `src/rag/vectorstore.py` — ChromaVectorStore | [Сделано] |
| 6 | Создать `src/rag/web_search.py` — DuckDuckGoSearchTool | [Сделано] |
| 7 | Создать `src/rag/prompts.py` — промпты для графа | [Сделано] |
| 8 | Создать `src/rag/graph.py` — LangGraph StateGraph | [Сделано] |
| 9 | Создать `src/rag/agent.py` — RAGClient (LLMClient) | [Сделано] |
| 10 | Обновить `src/core/config.py` — добавить RAG поля | [Сделано] |
| 11 | Обновить `src/core/pipeline.py` — логика выбора RAG | [Сделано] |
| 12 | Обновить `src/cli/app.py` — команды rag-* | [Сделано] |
| 13 | Обновить `requirements.txt` и `.env.example` | [Сделано] |
| 14 | Создать тесты `tests/test_rag/` | [Сделано] |
| 15 | Запустить тесты, mypy, ruff | [Сделано] |
| 16 | Streaming для RAG (оптимизация для TTS) | [Нужно сделать] |
| 17 | UI для управления RAG | [Нужно сделать] |
| 18 | Fallback между провайдерами | [Нужно сделать] |

---

### Планы на будущее

#### Приоритет: Высокий

1. **Streaming для RAG**
   - Реализовать настоящий streaming через `graph.astream()`
   - Буферизация для TTS (накапливать предложения перед озвучиванием)
   - Опция `rag_streaming: bool` в конфигурации

2. **Автоопределение темы для router**
   - Анализировать PDF документы для определения домена
   - Генерировать специфичные инструкции для router на основе контента
   - Кэширование темы в `data/rag_topic.json`

3. **Мониторинг производительности**
   - Замер latency для каждого узла графа
   - Статистика успешности routing (vectorstore vs websearch)
   - Логирование количества retry

#### Приоритет: Средний

4. **Поддержка дополнительных форматов документов**
   - Markdown файлы
   - TXT файлы
   - DOCX (через `python-docx`)
   - HTML (через `BeautifulSoup`)

5. **Улучшение веб-поиска**
   - Интеграция с Google Search API (если DuckDuckGo блокируется)
   - Интеграция с Tavily API (платный, но более надёжный)
   - Кэширование результатов поиска

6. **Multi-modal RAG**
   - Поддержка изображений в PDF (OCR через `pytesseract`)
   - Извлечение таблиц и графиков
   - Векторизация изображений (через CLIP)

#### Приоритет: Низкий

7. **Distributed RAG**
   - Поддержка распределённого ChromaDB (через HTTP API)
   - Шардирование vectorstore по темам
   - Репликация для отказоустойчивости

8. **Advanced retrieval strategies**
   - Hybrid search (vector + keyword)
   - Re-ranking через cross-encoder
   - Query expansion через LLM

9. **RAG evaluation framework**
   - Автоматическая оценка качества ответов
   - A/B тестирование разных стратегий
   - Human-in-the-loop feedback

---

## 3. Технические детали

### Зависимости

```txt
langgraph>=0.2.0
chromadb>=0.5.0
pypdf>=4.0.0
duckduckgo-search>=6.0.0
langchain-huggingface>=0.1.0
langchain-chroma>=1.1.0
langchain-text-splitters>=1.1.0
langchain-community>=0.4.0
```

### Конфигурация

```env
# .env
# RAG (Retrieval-Augmented Generation)
# Активируется автоматически, если в RAG_PDF_DIRECTORY есть PDF файлы
RAG_PDF_DIRECTORY=data/pdf
RAG_CHROMA_DIR=data/chroma_db
RAG_EMBEDDING_MODEL=intfloat/multilingual-e5-large
RAG_EMBEDDING_DEVICE=cpu
RAG_CHUNK_SIZE=1024
RAG_CHUNK_OVERLAP=200
RAG_RETRIEVER_K=3
RAG_MAX_RETRIES=3
RAG_USE_WEB_SEARCH=true
RAG_LLM_TEMPERATURE=0.0
```

### Пример использования

```python
from src.core.config import config
from src.rag.agent import RAGClient, create_rag_config

# Создать RAG клиент
rag_config = create_rag_config(config)
client = RAGClient(rag_config)

# Сканировать PDF директорию
count = client.scan_pdf_directory()
print(f"Добавлено чанков: {count}")

# Запрос к RAG агенту
messages = [{"role": "user", "content": "Что такое сортировка?"}]
result = asyncio.run(client.chat(messages))
print(result)

# Получить статистику
stats = client.get_stats()
print(f"Документов: {stats['document_count']}")
```

### Тестирование

```bash
# Запустить все тесты
python -m pytest tests/ -v

# Запустить только RAG тесты
python -m pytest tests/test_rag/ -v

# Проверить типизацию
python -m mypy src/rag/ --strict

# Проверить стиль кода
python -m ruff check src/rag/
```

**Результаты:**
- ✅ 130 тестов пройдено (18 новых RAG тестов)
- ✅ mypy --strict для `src/rag/`: 0 ошибок
- ✅ ruff check для `src/rag/`: 0 ошибок

---

## 4. Известные проблемы

| # | Проблема | Workaround |
|---|----------|------------|
| 1 | `langchain-community` deprecated | Используется `pypdf` напрямую вместо `PyPDFLoader` |
| 2 | DuckDuckGo может блокироваться | Можно переключиться на Google Search API или Tavily |
| 3 | Embedding модель загружается при первом запуске | Модель кэшируется в `~/.cache/huggingface/` |
| 4 | ChromaDB может быть медленным при большом объёме | Использовать `persist_directory` для persistence |
| 5 | LLM может не возвращать валидный JSON для grading | Используется `_safe_json_loads()` с regex extraction |

---

## 5. Changelog

### Добавлено
- `src/rag/` модуль с 9 файлами для RAG агента
- `RAGClient` реализует протокол `LLMClient` для интеграции в pipeline
- LangGraph state machine с маршрутизацией, grading, генерацией и веб-поиском
- ChromaVectorStore для persistence vector store
- PDFDocumentLoader для загрузки и чанкинга PDF
- DuckDuckGoSearchTool для веб-поиска
- 11 полей конфигурации в `Config` для настройки RAG
- 4 CLI команды: `rag-scan`, `rag-query`, `rag-stats`, `rag-clear`
- Автоактивация RAG при наличии PDF в `data/pdf/`
- 18 unit тестов для RAG модулей

### Изменено
- `src/core/pipeline.py` — добавлена логика выбора RAG client при наличии PDF
- `src/cli/app.py` — добавлены RAG команды и вывод RAG настроек в `show-config`
- `requirements.txt` — добавлены 8 зависимостей для RAG
- `.env.example` — добавлен блок RAG настроек
- `pyproject.toml` — добавлены mypy overrides для новых библиотек

### Исправлено
- Убран `langchain-community.document_loaders.PyPDFLoader` (deprecated) в пользу `pypdf` напрямую
- Исправлены line too long ошибки в `src/rag/graph.py`
- Добавлены type hints для всех публичных методов

---

## 6. Ссылки

- **LangGraph:** https://langchain-ai.github.io/langgraph/
- **ChromaDB:** https://docs.trychroma.com/
- **DuckDuckGo Search:** https://github.com/deedy5/duckduckgo_search
- **HuggingFace Embeddings:** https://huggingface.co/intfloat/multilingual-e5-large
- **pypdf:** https://pypdf.readthedocs.io/

---

**Конец отчёта**
