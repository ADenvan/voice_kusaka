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
