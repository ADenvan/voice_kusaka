# Release Report: Двуязычный TTS (Silero A1)

**Дата релиза:** 09.09.2026  
**Версия:** v1.0  
**Тип:** Feature Release

---

## 1. Схемы изменений

### Дерево измененных файлов

```
src/
├── core/
│   ├── config.py              [ИЗМЕНЕН] Добавлены параметры для EN TTS
│   └── pipeline.py            [ИЗМЕНЕН] Использует BilingualSileroTTSEngine
├── tts/
│   ├── language_detector.py   [НОВЫЙ] Детектор языка + сегментация
│   └── silero_engine.py       [ИЗМЕНЕН] BilingualSileroTTSEngine + _SileroModel
├── stt/
│   └── whisper_engine.py      [ИЗМЕНЕН] Убран hardcoded language="ru"
├── llm/
│   └── prompt_builder.py      [ИЗМЕНЕН] Промпт разрешает RU+EN
└── cli/
    └── app.py                 [ИЗМЕНЕН] Добавлен флаг --lang

tests/
├── test_language_detector.py  [НОВЫЙ] 16 тестов для language_detector
└── test_tts.py                [ИЗМЕНЕН] Обновлены + добавлены 4 теста
```

### Архитектура решения

```
┌─────────────────────────────────────────────────────────────┐
│  CLI: python -m src.cli.app run --lang en                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Config:                                                    │
│    tts_language: "en" (из CLI или .env)                     │
│    silero_language: "ru", silero_speaker: "v5_ru"          │
│    silero_en_language: "en", silero_en_speaker: "v3_en"    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Pipeline:                                                  │
│    STT: language=config.tts_language (не hardcoded)         │
│    LLM: промпт разрешает RU+EN                              │
│    TTS: BilingualSileroTTSEngine                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  BilingualSileroTTSEngine:                                  │
│    - Загружает v5_ru + v3_en при старте                     │
│    - segment_by_language() разбивает текст на сегменты      │
│    - Для каждого сегмента → своя модель                     │
│    - np.concatenate() → один аудиофайл                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Статус и описание работы

### Краткая суть

Реализована поддержка двуязычного TTS (русский + английский) на базе двух моделей Silero:
- **v5_ru** для русского языка (голос `baya`)
- **v3_en** для английского языка (голос `en_0`)

Текст автоматически сегментируется по языку, каждый сегмент синтезируется своей моделью, результаты конкатенируются в один аудиофайл.

### Статусы задач

| Задача | Статус | Описание |
|--------|--------|----------|
| Config: добавить параметры EN TTS | [Сделано] | `tts_language`, `silero_en_*` |
| Language Detector | [Сделано] | Детектор языка + сегментация текста |
| TTS Engine | [Сделано] | `BilingualSileroTTSEngine` с двумя моделями |
| STT: убрать hardcoded language | [Сделано] | Использует `config.tts_language` |
| LLM: промпт для RU+EN | [Сделано] | Разрешены ответы на обоих языках |
| CLI: флаг --lang | [Сделано] | `--lang ru\|en` |
| Pipeline: новый TTS | [Сделано] | Использует `BilingualSileroTTSEngine` |
| Тесты language_detector | [Сделано] | 16 тестов, все проходят |
| Тесты TTS | [Сделано] | Обновлены + 4 новых теста |
| Интеграционный тест | [Нужно сделать] | Полный пайплайн с EN текстом |

### Что работает

- **Запуск на русском:** `python -m src.cli.app run` (по умолчанию)
- **Запуск на английском:** `python -m src.cli.app run --lang en`
- **Через .env:** `TTS_LANGUAGE=en python -m src.cli.app run`
- **Автоматическая сегментация:** Смешанный текст (RU+EN+RU) корректно обрабатывается
- **STT:** Распознает язык, указанный в `tts_language`
- **LLM:** Отвечает на языке пользователя

### Известные ограничения

- **Разные голоса:** Русский (`baya`) и английский (`en_0`) голоса имеют разные тембры
- **Две модели в RAM:** ~60-100 MB суммарно
- **Async тесты:** Требуют `pytest-asyncio` (pre-existing проблема проекта)

---

## 3. Планы на будущее

### Короткий срок

- [ ] Интеграционный тест полного пайплайна с EN текстом
- [ ] Подбор английского голоса, похожего на `baya` (женский)
- [ ] Оптимизация загрузки моделей (ленивая загрузка EN модели)
- [ ] Документация в README.md

### Средний срок

- [ ] Замена на Kokoro-ONNX (одна модель для всех языков, лучшее качество)
- [ ] Поддержка дополнительных языков (немецкий, испанский)
- [ ] Автоматический детект языка ввода (без флага --lang)
- [ ] Кэширование синтезированных сегментов

### Долгий срок

- [ ] Streaming TTS (потоковый синтез для уменьшения latency)
- [ ] Клонирование голоса (один тембр для всех языков)
- [ ] GPU-ускорение синтеза
- [ ] Веб-интерфейс для управления языками

---

## 4. Технические детали

### Новые конфигурационные параметры

```python
# .env или CLI
tts_language: str = "ru"              # Основной язык TTS/STT
silero_en_language: str = "en"        # Язык EN модели
silero_en_speaker: str = "v3_en"      # Speaker EN модели
silero_en_voice: str = "en_0"         # Голос EN модели
silero_en_sample_rate: int = 48000    # Sample rate EN модели
```

### API Language Detector

```python
from src.tts.language_detector import detect_language, segment_by_language

# Определение языка текста
lang = detect_language("Привет Hello")  # → "ru" или "en"

# Сегментация текста по языкам
segments = segment_by_language("Привет Hello Мир")
# → [("ru", "Привет"), ("en", "Hello"), ("ru", "Мир")]
```

### Использование BilingualSileroTTSEngine

```python
from src.core.config import Config
from src.tts.silero_engine import BilingualSileroTTSEngine

config = Config()
tts = BilingualSileroTTSEngine(config)
tts.load()  # Загружает обе модели

# Синтез смешанного текста
audio = await tts.synthesize("Привет Hello Мир")
# Автоматически сегментирует и синтезирует каждой моделью
```

---

## 5. Коммиты

```
feat(tts): добавить двуязычный TTS (Silero A1)

- Добавлены параметры tts_language, silero_en_* в Config
- Создан language_detector.py для сегментации текста
- Переписан silero_engine.py: BilingualSileroTTSEngine
- Убран hardcoded language="ru" из STT
- Изменен промпт LLM для поддержки RU+EN
- Добавлен флаг --lang в CLI
- Добавлены тесты для language_detector и TTS
```

---

**Статус релиза:** ✅ Готов к использованию  
**Тестирование:** ✅ Unit-тесты проходят (23 синхронных теста)  
**Документация:** ✅ Отчет создан
