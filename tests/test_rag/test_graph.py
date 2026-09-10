import json

import pytest

from src.rag.graph import RAGGraphState, _format_docs, _safe_json_loads
from langchain_core.documents import Document


def test_safe_json_loads_valid() -> None:
    result = _safe_json_loads('{"key": "value"}')
    assert result == {"key": "value"}


def test_safe_json_loads_with_markdown() -> None:
    result = _safe_json_loads('```json\n{"key": "value"}\n```')
    assert result == {"key": "value"}


def test_safe_json_loads_with_extra_text() -> None:
    result = _safe_json_loads('Some text {"key": "value"} more text')
    assert result == {"key": "value"}


def test_safe_json_loads_invalid() -> None:
    with pytest.raises(json.JSONDecodeError):
        _safe_json_loads("not json at all")


def test_format_docs() -> None:
    docs = [
        Document(page_content="doc 1"),
        Document(page_content="doc 2"),
    ]
    result = _format_docs(docs)
    assert result == "doc 1\n\ndoc 2"


def test_format_docs_empty() -> None:
    result = _format_docs([])
    assert result == ""
