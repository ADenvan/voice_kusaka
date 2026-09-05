# Project Structure Guide

Best practices for organizing Python projects.

## Standard Project Layout

### Basic Project Structure

```
myproject/
├── README.md                  # Project overview
├── LICENSE                    # License file
├── pyproject.toml            # Modern Python packaging
├── setup.py                  # Legacy packaging (optional)
├── setup.cfg                 # Legacy configuration (optional)
├── requirements.txt          # Dependencies
├── requirements-dev.txt      # Development dependencies
├── .gitignore               # Git ignore rules
├── .pre-commit-config.yaml  # Pre-commit hooks
├── tox.ini                   # Test environments
├── Makefile                  # Common tasks
│
├── src/                     # Source code
│   └── myproject/
│       ├── __init__.py      # Package init
│       ├── __main__.py      # Entry point
│       ├── core/            # Core functionality
│       │   ├── __init__.py
│       │   ├── models.py
│       │   └── services.py
│       ├── utils/           # Utilities
│       │   ├── __init__.py
│       │   ├── helpers.py
│       │   └── validators.py
│       └── cli.py           # Command-line interface
│
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── conftest.py         # Pytest fixtures
│   ├── unit/               # Unit tests
│   │   ├── __init__.py
│   │   ├── test_models.py
│   │   └── test_services.py
│   ├── integration/        # Integration tests
│   │   ├── __init__.py
│   │   └── test_api.py
│   └── e2e/                # End-to-end tests
│       └── __init__.py
│
├── docs/                    # Documentation
│   ├── conf.py             # Sphinx configuration
│   ├── index.rst
│   ├── api.rst
│   └── usage.rst
│
├── scripts/                 # Utility scripts
│   ├── setup.sh
│   └── deploy.sh
│
└── examples/                # Usage examples
    ├── basic_usage.py
    └── advanced_usage.py
```

### Alternative: Flat Layout

For simpler projects:

```
myproject/
├── README.md
├── LICENSE
├── pyproject.toml
├── requirements.txt
├── myproject.py            # Single-module project
├── test_myproject.py
└── examples/
    └── example.py
```

## Configuration Files

### pyproject.toml (Recommended)

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "myproject"
version = "1.0.0"
description = "A short description of the project"
readme = "README.md"
license = {file = "LICENSE"}
authors = [
    {name = "Your Name", email = "you@example.com"}
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
requires-python = ">=3.10"
dependencies = [
    "requests>=2.28.0",
    "pydantic>=2.0.0",
    "click>=8.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
    "pre-commit>=3.0.0",
]
docs = [
    "sphinx>=6.0.0",
    "sphinx-rtd-theme>=1.2.0",
]

[project.scripts]
myproject = "myproject.cli:main"

[project.urls]
Homepage = "https://github.com/username/myproject"
Documentation = "https://myproject.readthedocs.io"
Repository = "https://github.com/username/myproject"
Issues = "https://github.com/username/myproject/issues"

# Tool configurations
[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 88
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
known_first_party = ["myproject"]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
warn_redundant_casts = true
warn_unused_ignores = true
show_error_codes = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short --strict-markers"
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
]

[tool.coverage.run]
source = ["src"]
omit = ["*/tests/*", "*/test_*.py"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
```

### setup.py (Legacy)

```python
"""Setup configuration (legacy, use pyproject.toml)."""
from setuptools import setup, find_packages

setup(
    name="myproject",
    version="1.0.0",
    description="A short description",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="you@example.com",
    url="https://github.com/username/myproject",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.28.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "ruff>=0.1.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "myproject=myproject.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
    ],
)
```

### requirements.txt

```
# Production dependencies
requests>=2.28.0
pydantic>=2.0.0
click>=8.0.0

# Pinned versions for reproducibility
# requests==2.31.0
# pydantic==2.5.0
```

### requirements-dev.txt

```
-r requirements.txt

# Testing
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-asyncio>=0.21.0
factory-boy>=3.3.0

# Linting and formatting
ruff>=0.1.0
mypy>=1.0.0

# Pre-commit hooks
pre-commit>=3.4.0

# Documentation
sphinx>=7.0.0
sphinx-rtd-theme>=1.3.0

# Development tools
ipython>=8.0.0
ipdb>=0.13.0
```

### .gitignore

```gitignore
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/
cover/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
.pybuilder/
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# pyenv
.python-version

# pipenv
Pipfile.lock

# poetry
poetry.lock

# pdm
.pdm.toml

# PEP 582
__pypackages__/

# Celery stuff
celerybeat-schedule
celerybeat.pid

# SageMath parsed files
*.sage.py

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Pyre type checker
.pyre/

# pytype static type analyzer
.pytype/

# Cython debug symbols
cython_debug/

# PyCharm
.idea/

# VS Code
.vscode/

# OS
.DS_Store
Thumbs.db
```

### .pre-commit-config.yaml

```yaml
# See https://pre-commit.com for more information
# See https://pre-commit.com/hooks.html for more hooks
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-json
      - id: check-toml
      - id: check-merge-conflict
      - id: debug-statements

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
```

## Package Structure

### __init__.py Patterns

```python
"""MyProject - A short description.

Longer description of what this package does.

Example:
    >>> from myproject import Client
    >>> client = Client()
    >>> client.do_something()
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "you@example.com"

# Export main classes/functions
from .client import Client
from .exceptions import MyProjectError, ValidationError

# Define __all__ for explicit exports
__all__ = [
    "Client",
    "MyProjectError",
    "ValidationError",
]
```

### Version Management

```python
# Single source of truth for version
# src/myproject/_version.py
__version__ = "1.0.0"

# src/myproject/__init__.py
from ._version import __version__
```

## Testing Structure

### conftest.py

```python
"""Pytest configuration and fixtures."""

import pytest
from myproject import Client


@pytest.fixture
def client():
    """Create a test client."""
    return Client(test_mode=True)


@pytest.fixture
def sample_data():
    """Provide sample data for tests."""
    return {
        "name": "Test User",
        "email": "test@example.com",
    }


@pytest.fixture(scope="session")
def db():
    """Set up test database."""
    # Setup
    database = create_test_database()
    yield database
    # Teardown
    database.cleanup()
```

### Test Organization

```python
# tests/unit/test_models.py
import pytest
from myproject.models import User


class TestUser:
    """Test User model."""
    
    def test_user_creation(self):
        """Test creating a user."""
        user = User(name="Alice", email="alice@example.com")
        assert user.name == "Alice"
        assert user.email == "alice@example.com"
    
    def test_user_validation(self):
        """Test user validation."""
        with pytest.raises(ValueError):
            User(name="", email="invalid")


# tests/integration/test_api.py
import pytest

@pytest.mark.integration
class TestAPI:
    """Integration tests for API."""
    
    def test_api_endpoint(self, client):
        """Test API endpoint."""
        response = client.get("/api/users")
        assert response.status_code == 200
```

## Documentation Structure

### README.md Template

```markdown
# MyProject

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Short description of the project.

## Features

- Feature 1
- Feature 2
- Feature 3

## Installation

```bash
pip install myproject
```

## Quick Start

```python
from myproject import Client

client = Client()
result = client.do_something()
```

## Development

```bash
# Clone repository
git clone https://github.com/username/myproject.git
cd myproject

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check src tests
ruff format src tests
mypy src
```

## License

[MIT](LICENSE)
```

## Makefile

```makefile
.PHONY: install test lint format clean docs

install:
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest -v --cov=src --cov-report=term-missing

test-unit:
	pytest tests/unit -v

test-integration:
	pytest tests/integration -v -m integration

lint:
	ruff check src tests
	mypy src
	isort --check-only src tests
	ruff format --check src tests

format:
	isort src tests
	ruff format src tests

mypy:
	mypy src

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docs:
	cd docs && make html

build: clean
	python -m build

twine-upload: build
	twine upload dist/*
```

## CI/CD Configuration

### GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Lint
        run: |
          ruff check src tests
          ruff format --check src tests
          isort --check-only src tests

      - name: Type check
        run: mypy src

      - name: Test
        run: pytest --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

## Common Patterns

### CLI Entry Point

```python
# src/myproject/__main__.py
"""Entry point for running as module."""

from myproject.cli import main

if __name__ == "__main__":
    main()
```

```python
# src/myproject/cli.py
"""Command-line interface."""

import click
from myproject import Client


@click.group()
@click.version_option()
def cli():
    """MyProject CLI."""
    pass


@cli.command()
@click.argument("input_file")
@click.option("--output", "-o", help="Output file")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def process(input_file: str, output: str | None, verbose: bool) -> None:
    """Process input file."""
    client = Client(verbose=verbose)
    client.process(input_file, output)


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
```

### Configuration Management

```python
# src/myproject/config.py
"""Configuration management."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Config:
    """Application configuration."""
    
    api_key: str
    base_url: str = "https://api.example.com"
    timeout: int = 30
    debug: bool = False
    
    @classmethod
    def from_env(cls) -> "Config":
        """Create config from environment variables."""
        return cls(
            api_key=os.environ["API_KEY"],
            base_url=os.environ.get("BASE_URL", "https://api.example.com"),
            timeout=int(os.environ.get("TIMEOUT", "30")),
            debug=os.environ.get("DEBUG", "").lower() == "true",
        )
```

## References

- Python Packaging: https://packaging.python.org/
- setuptools: https://setuptools.pypa.io/
- pytest: https://docs.pytest.org/
- Sphinx: https://www.sphinx-doc.org/
