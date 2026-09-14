# Python Project Rules

## Security

### Pre-Commit
- [ ] No hardcoded secrets (use `os.environ`)
- [ ] Input validation
- [ ] SQL injection prevention (parameterized queries)
- [ ] Error messages don't leak data

### Secrets
```python
# WRONG
API_KEY = "sk-xxx"

# RIGHT
import os
API_KEY = os.environ.get("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY not set")
```

---

## Code Style

### Type Hints
```python
def process(data: dict[str, int]) -> list[str]:
    ...
```

### Immutability
```python
from dataclasses import replace

def update(user, name: str):
    return replace(user, name=name)
```

### Naming
- Use descriptive English names for functions and variables
- If code repeats >2 times → extract to function

### Documentation
- Every function must have a short docstring/description before definition

### Quality Checklist
- [ ] Type hints on all functions
- [ ] Functions < 50 lines
- [ ] No `print()` statements (use `loguru.logger`)
- [ ] Ruff formatting passed

---

## Logging

- **Library**: `loguru` (установлена как `loguru==0.7.3`)
- **Импорт**: `from loguru import logger`
- **Правило**: Никаких `print()` — только `logger.info()`, `logger.debug()`, `logger.error()` и т.д.
- **Конфигурация**: Использовать `logger.add()` для кастомных sinks (файл, консоль и т.д.)

### Пример:
```python
from loguru import logger

logger.info("Starting voice assistant...")
logger.debug("Audio device: {}", device_name)
logger.error("Failed to initialize STT: {}", error)
```

---

## Testing (80%+ Coverage)

### Workflow
1. Write test
2. Run: `pytest` (should FAIL)
3. Implement
4. Run: `pytest --cov` (should PASS, 80%+)

---

## Commands

```bash
# Format & Lint
ruff format .
ruff check . --fix

# Type Check
mypy .

# Test
pytest
pytest --cov

# Security
pip-audit
bandit -r .
```

---

## Project Structure Rules

- **`pyproject.toml`** — the single source of truth for metadata, dependencies, and tool configuration.
- **Never edit auto-generated directories or files:**
  - `*.egg-info/` (PKG-INFO, requires.txt, SOURCES.txt, etc.)
  - `__pycache__/`
  - `.pytest_cache/`
  - `.mypy_cache/`
  - `build/`, `dist/`
- All changes to versions, dependencies, and linter settings must be managed exclusively via `pyproject.toml`.
- When `pyproject.toml` changes, rebuild the environment: `pip install -e . --group dev`.
- **`requirements.txt`** and **`requirements-dev.txt`** are kept for backward compatibility and manual installs.
<!-- - When `requirements.txt` or `requirements-dev.txt` changes, reinstall dependencies:
  - Full reinstall: `pip install -r requirements.txt -r requirements-dev.txt`
  - Or use `pip-sync requirements.txt requirements-dev.txt` (если установлен `pip-tools`) -->
---

<!-- ## Agents

| Agent | Use When |
|-------|----------|
| tdd-guide | New features, bugs |
| code-reviewer | After writing code |
| security-reviewer | Before commits |

--- -->


## Success Criteria
- Tests pass (80%+ coverage)
- No security issues
- Ruff clean
- Type hints complete
- No `print()` statements
