from unittest.mock import MagicMock, patch

from src.rag.web_search import DuckDuckGoSearchTool


def test_search_returns_combined_results() -> None:
    tool = DuckDuckGoSearchTool(max_results=2)
    fake_results = [
        {"body": "first result body"},
        {"body": "second result body"},
    ]
    mock_ddgs = MagicMock()
    mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
    mock_ddgs.__exit__ = MagicMock(return_value=False)
    mock_ddgs.text.return_value = iter(fake_results)

    with patch("src.rag.web_search.DDGS", return_value=mock_ddgs):
        result = tool.search("test query")

    assert "first result body" in result
    assert "second result body" in result
    assert "\n\n" in result


def test_search_returns_empty_when_no_results() -> None:
    tool = DuckDuckGoSearchTool()
    mock_ddgs = MagicMock()
    mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
    mock_ddgs.__exit__ = MagicMock(return_value=False)
    mock_ddgs.text.return_value = iter([])

    with patch("src.rag.web_search.DDGS", return_value=mock_ddgs):
        result = tool.search("test query")

    assert result == ""


def test_search_ignores_results_without_body() -> None:
    tool = DuckDuckGoSearchTool()
    fake_results = [
        {"body": "keep this"},
        {"title": "no body"},
        {"body": "and this"},
    ]
    mock_ddgs = MagicMock()
    mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
    mock_ddgs.__exit__ = MagicMock(return_value=False)
    mock_ddgs.text.return_value = iter(fake_results)

    with patch("src.rag.web_search.DDGS", return_value=mock_ddgs):
        result = tool.search("test query")

    assert result == "keep this\n\nand this"


def test_search_handles_exception() -> None:
    tool = DuckDuckGoSearchTool()

    with patch("src.rag.web_search.DDGS", side_effect=RuntimeError("network error")):
        result = tool.search("test query")

    assert result == ""
