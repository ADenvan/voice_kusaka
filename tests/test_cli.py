from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from src.cli.app import app

runner = CliRunner()


def test_show_config() -> None:
    result = runner.invoke(app, ["show-config"])
    assert result.exit_code == 0
    assert "whisper_model" in result.output
    assert "llm_model" in result.output


def test_models_command_fails_gracefully() -> None:
    result = runner.invoke(app, ["models"])
    assert result.exit_code == 0
    assert (
        "Ошибка" in result.output
        or "Нет" in result.output
        or "ollama" in result.output.lower()
        or "lmstudio" in result.output.lower()
        or "Провайдер" in result.output
    )


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.output
    assert "chat" in result.output
    assert "models" in result.output


def test_run_help() -> None:
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "model" in result.output


@patch("src.rag.agent.RAGClient")
def test_rag_stats(mock_client: MagicMock) -> None:
    mock_client.return_value.get_stats.return_value = {
        "document_count": 42,
        "index_dir": "data/faiss_index",
    }
    result = runner.invoke(app, ["rag-stats"])
    assert result.exit_code == 0
    assert "42" in result.output
    assert "data/faiss_index" in result.output


@patch("src.rag.agent.RAGClient")
def test_rag_clear(mock_client: MagicMock) -> None:
    result = runner.invoke(app, ["rag-clear"])
    assert result.exit_code == 0
    mock_client.return_value.clear_vectorstore.assert_called_once()


@patch("src.rag.agent.RAGClient")
def test_rag_scan(mock_client: MagicMock) -> None:
    mock_client.return_value.scan_pdf_directory.return_value = 10
    result = runner.invoke(app, ["rag-scan", "--directory", "data/pdf"])
    assert result.exit_code == 0
    assert "10" in result.output
    mock_client.return_value.scan_pdf_directory.assert_called_once_with("data/pdf")


@patch("src.rag.agent.RAGClient")
def test_rag_query(mock_client: MagicMock) -> None:
    mock_client.return_value.chat = AsyncMock(return_value="test answer")
    result = runner.invoke(app, ["rag-query", "what is ai?"])
    assert result.exit_code == 0
    assert "test answer" in result.output
    mock_client.return_value.chat.assert_called_once()


@patch("src.rag.agent.RAGClient")
def test_rag_scan_default_directory(mock_client: MagicMock) -> None:
    mock_client.return_value.scan_pdf_directory.return_value = 7
    result = runner.invoke(app, ["rag-scan"])
    assert result.exit_code == 0
    assert "7" in result.output


def test_models_invalid_provider() -> None:
    result = runner.invoke(app, ["models", "--provider", "invalid"])
    assert result.exit_code == 1
    assert "provider must be" in result.output


@patch("src.cli.app.get_llm_client")
def test_models_lists_models(mock_client: MagicMock) -> None:
    mock_client.return_value.list_models = AsyncMock(return_value=["model-a", "model-b"])
    result = runner.invoke(app, ["models", "--provider", "ollama"])
    assert result.exit_code == 0
    assert "model-a" in result.output
    assert "model-b" in result.output
