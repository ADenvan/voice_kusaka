# Release Report: RAG Modes Implementation

**Дата релиза:** 2026-09-14  
**Версия:** v0.2.0  
**Статус:** ✅ Завершено

---

## 1. Схемы изменений

### Python-код

```
src/
├── core/
│   └── config.py                      # Добавлены rag_mode и rag_timeout
├── cli/
│   └── app.py                         # Добавлен флаг --rag-mode для команды run
└── rag/
    ├── config.py                      # Добавлены mode и timeout
    ├── graph.py                       # Реализованы 3 режима графа: simple/routing/full
    ├── agent.py                       # Обновлен для передачи mode и timeout
    └── prompts.py                     # Исправлены escape-последовательности в JSON-примерах

tests/
└── test_rag/
    └── test_graph.py                  # Добавлены тесты для всех режимов и узлов графа

.env                                   # Добавлены RAG_MODE и RAG_TIMEOUT
.env.example                           # Добавлены RAG_MODE и RAG_TIMEOUT
```

### Архитектура графов

#### Simple Mode (по умолчанию)
```
retrieve → should_web_search → generate → END
                ↓ (если пусто)
            web_search → generate → END
```

#### Routing Mode
```
route_question (LLM)
       ↓
   ┌───┴───────────┐
   ↓               ↓
retrieve       web_search
   ↓               ↓
grade_documents    ↓
   ↓               ↓
decide_to_generate ←┘
   ↓
generate → END
```

#### Full Mode
```
route_question (LLM)
       ↓
   ┌───┴───────────┐
   ↓               ↓
retrieve       web_search
   ↓               ↓
grade_documents    ↓
   ↓               ↓
decide_to_generate ←┘
   ↓
generate
   ↓
grade_generation (hallucination + answer quality)
   ↓
   ├── useful → END
   ├── not_useful → web_search → generate
   ├── not_supported → generate (retry)
   └── max_retries → END
```

---

## 2. Статус и описание работы

### Краткая суть

Реализована гибкая система RAG-графов с тремя режимами работы, позволяющая балансировать между скоростью и качеством ответов:

- **simple** — быстрая обработка без дополнительных LLM-вызовов (по умолчанию)
- **routing** — LLM-маршрутизация + оценка релевантности документов
- **full** — полный цикл с проверкой галлюцинаций и качества ответов

Режим выбирается через:
1. CLI флаг `--rag-mode` (приоритет выше)
2. Переменную окружения `RAG_MODE`
3. Значение по умолчанию `simple`

### Статусы задач

- [Сделано] Добавлены поля `rag_mode` и `rag_timeout` в конфигурации
- [Сделано] Реализованы три режима графа в `RAGGraphBuilder`
- [Сделано] Добавлены узлы: `route_question`, `grade_documents`, `decide_to_generate`, `grade_generation`
- [Сделано] Реализован безопасный парсинг JSON из ответов LLM
- [Сделано] Добавлен CLI флаг `--rag-mode` для команды `run`
- [Сделано] Обновлены `.env` и `.env.example` с новыми параметрами
- [Сделано] Исправлены escape-последовательности в промптах (`{{binary_score}}`)
- [Сделано] Добавлены тесты для всех режимов и узлов графа
- [Сделано] Все тесты проходят (192/192), покрытие 81%
- [Сделано] Код проходит проверки ruff

### Планы на будущее

- [ ] Добавить метрики для мониторинга качества ответов в разных режимах
- [ ] Реализовать автоматический выбор режима на основе сложности вопроса
- [ ] Добавить поддержку кэширования для повторяющихся запросов
- [ ] Оптимизировать количество LLM-вызовов в full режиме
- [ ] Добавить визуализацию графов для отладки

---

## 3. Использование

### Запуск с простым режимом (по умолчанию)
```bash
python -m src.cli.app run --provider lmstudio --mode button
```

### Запуск с routing режимом
```bash
python -m src.cli.app run --provider lmstudio --mode button --rag-mode routing
```

### Запуск с full режимом
```bash
python -m src.cli.app run --provider lmstudio --mode button --rag-mode full
```

### Настройка через .env
```env
RAG_MODE=simple  # simple | routing | full
RAG_TIMEOUT=180  # таймаут для графа в секундах
```

---

## 4. Известные ограничения

- **routing** и **full** режимы требуют больше LLM-вызовов (3-6 на запрос)
- JSON-парсинг может падать на нестандартных ответах LLM (используется fallback)
- Full режим может быть медленным для сложных вопросов (до 180 секунд)
- Reasoning-модели (qwen3.5-9b-python-coder) могут возвращать пустой `content`

---

## 5. Тестирование

```bash
# Запустить все тесты
python -m pytest --cov -m "not integration"

# Проверить покрытие
python -m pytest --cov=src --cov-report=term-missing

# Проверить код
python -m ruff check src/ tests/
```

**Результаты:**
- ✅ 192 теста пройдено
- ✅ 81% покрытие кода
- ✅ ruff проверки пройдены

---

## 6. Миграция

Для существующих установок:

1. Обновите `.env`:
   ```bash
   echo "RAG_MODE=simple" >> .env
   echo "RAG_TIMEOUT=180" >> .env
   ```

2. Или используйте значения по умолчанию (настройка не обязательна)

3. Для тестирования новых режимов:
   ```bash
   python -m src.cli.app rag-query "Ваш вопрос" --provider lmstudio --rag-mode routing
   ```

---

**Подпись:** AI Assistant  
**Дата:** 2026-09-14
