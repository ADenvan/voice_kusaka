
# У тебя используется [dependency-groups], а НЕ [project.optional-dependencies].
**Новый стандарт** - PEP 735 (dependency-groups)

```bash
# Активируй venv в VSCode (если не активирован)
# Ctrl+Shift+P → "Python: Select Interpreter" → выбери .venv
# Первоначальная установка
pip install -e . --group dev

# После изменения зависимостей в pyproject.toml
pip install -e . --group dev

# Только runtime (без dev)
pip install -e .

# Проверка что пакет установлен
pip list --editable
```

# Когда нужно переустанавливать

1. pip install -e .
  - Добавил зависимость в pyproject.toml - Добавил "requests>=2.0" в dependencies

2. pip install -e . --group dev
  - Изменил [dependency-groups] dev - Добавил "black" в [dependency-groups]
```txt
pip install -e .
     ↓
Создаёт файл: .venv/Lib/site-packages/voice_ai.pth
     ↓
Содержимое: D:\Python-Project\app_try\voice_kusaka\src
     ↓
Python при `import voice_ai` идёт напрямую в эту папку
```