# Release Report: Исправление голосового конвейера и миграция RAG на FAISS

**Дата:** 2026-09-14
**Версия:** 0.1.0
**Контекст:** Исправление ситуации, когда голосовой ассистент принимал вопрос после STT, но не произносил ответ и возвращался к состоянию ожидания активации.

---

## 1. Схемы изменений

### 1.1. Python-код — затронутые файлы

```
voice_kusaka/
├── src/
│   ├── cli/
│   │   └── app.py                      # Добавлены --provider и --model для rag-query
│   ├── core/
│   │   ├── config.py                   # Исправлен дефолтный llm_base_url для LM Studio
│   │   └── pipeline.py                 # Fallback при пустом ответе LLM
│   └── rag/
│       ├── agent.py                    # Исправлен _run_graph: ожидание непустого generation
│       ├── graph.py                    # Логирование этапов retrieve/generate
│       ├── prompts.py                  # Fallback на общие знания при пустом контексте
│       ├── vectorstore.py              # Реализация FaissVectorStore
│       └── config.py                   # Поле faiss_index_dir вместо chroma_persist_dir
├── tests/
│   └── test_config.py                  # Обновлены ожидания дефолтов
├── .env                                # Дефолты переключены на LM Studio
├── .env.example                        # Актуализирован под FAISS и LM Studio
├── pyproject.toml                      # Полный список runtime/dev-зависимостей
└── requirements.txt                    # Убран chromadb, добавлен faiss-cpu
```

### 1.2. Конвейер данных (Data flow)

```
[Микрофон] → [VAD] → [STT faster-whisper] → [RAGClient]
                                                  ↓
                                          [FAISS retriever]
                                                  ↓
                                          [LLM generate]
                                                  ↓
                                          [TTS silero] → [Колонки]
```

### 1.3. Архитектура RAG-графа

```
        ┌─────────────┐
        │   retrieve  │
        └──────┬──────┘
               │
       ┌───────┴───────┐
       │ documents == 0│
       │  и web-search │
       │   включен     │
       └───────┬───────┘
        ДА /           \ НЕТ
           /             \
┌──────────────┐    ┌──────────┐
│  web_search  │───→│ generate │
└──────────────┘    └────┬─────┘
                         │
                    ┌────┴────┐
                    │   END   │
                    └─────────┘
```

---

## 2. Статус и описание работы

### 2.1. Краткая суть

Выполнена миграция векторного хранилища с ChromaDB на FAISS и исправлена ошибка, из-за которой RAG-агент всегда возвращал пустую строку: `_run_graph` завершался на начальном состоянии графа, где `generation=""`, не дожидаясь ответа LLM. Добавлены fallback-ответы, логирование ключевых этапов и возможность тестировать RAG через `rag-query` с теми же флагами `--provider`/`--model`, что и в голосовом режиме.

### 2.2. Статусы задач

- [Сделано] Миграция RAG-хранилища с ChromaDB на FAISS (`FaissVectorStore`, `data/faiss_index`).
- [Сделано] Упрощение RAG-графа: убраны JSON-router, grader и hallucination-grader, оставлены `retrieve → (web_search) → generate`.
- [Сделано] Исправлен `RAGClient._run_graph`: теперь возвращается последнее непустое значение `generation`.
- [Сделано] Добавлен fallback в `pipeline.py` при пустом ответе LLM.
- [Сделано] Обновлён `RAG_PROMPT`: разрешён ответ из общих знаний при отсутствии релевантного контекста.
- [Сделано] Добавлены флаги `--provider` и `--model` для команды `rag-query`.
- [Сделано] Исправлен дефолтный `llm_base_url` в `config.py` для провайдера LM Studio.
- [Сделано] Актуализированы `.env` и `.env.example`: LM Studio по умолчанию, `RAG_FAISS_DIR` вместо `RAG_CHROMA_DIR`.
- [Сделано] Дополнен `pyproject.toml` полным набором runtime- и dev-зависимостей.
- [Сделано] Тесты: 176 passed, покрытие 80%.
- [В процессе] Требуется проверка голосового режима `--mode button` с LM Studio в реальном времени.
- [Нужно сделать] Поддержка системного сообщения (`system` role) внутри RAG-графа для единообразия с `UnifiedLLMClient`.
- [Нужно сделать] Добавить health-check модели для `RAGClient` перед вызовом графа (аналог `check_llm_health`).
- [Нужно сделать] Убрать устаревший `langchain-community` и перейти на standalone FAISS-интеграцию (сейчас есть DeprecationWarning).

### 2.3. Планы на будущее

1. **Полная интеграция с LangGraph ReAct-агентом** — добавить tool-calling для веб-поиска и других инструментов через `langgraph.prebuilt`.
2. **Конфигурация RAG-температуры и max_tokens** — вынести `rag_llm_max_tokens` в `.env`, чтобы контролировать длину ответа.
3. **Streaming-ответы в RAG** — заменить `ainvoke`/`invoke` на `astream`, чтобы TTS начинал озвучку до полного завершения генерации.
4. **Мониторинг качества retrieval** — логировать score retrieved-документов и добавить reranker.
5. **Поддержка нескольких языков TTS** — автоматическое переключение `silero_language` на основе определённого языка запроса.
6. **Docker-образ** — упаковка приложения для запуска без ручной установки зависимостей.

---

## 3. Метрики качества

| Показатель | Значение |
|------------|----------|
| Тесты пройдены | 176 / 176 |
| Покрытие кода | 80% |
| Ruff (изменённые файлы) | чисто |
| Критические баги | 0 (основной баг с пустым ответом исправлен) |

---

## 4. Как проверить

```bash
# 1. Текстовый RAG-запрос через LM Studio
python -m src.cli.app rag-query "Что такое алгоритмы?" --provider lmstudio --model qwen3.5-9b-python-coder
python -m src.cli.app rag-query "Найди в Интернети примеры python код что такое Объекты ?" --provider lmstudio --model qwen3.5-9b-python-coder

# 2. Голосовой режим
python -m src.cli.app run --provider lmstudio --mode button --model qwen3.5-9b-python-coder

# 3. Тесты и покрытие
python -m pytest --cov -m "not integration"
```
