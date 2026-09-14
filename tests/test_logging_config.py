from unittest.mock import MagicMock, patch

from src.core.logging_config import setup_logging


def test_setup_logging_configures_handlers() -> None:
    mock_stderr = MagicMock()
    with (
        patch("src.core.logging_config.logger") as mock_logger,
        patch("src.core.logging_config.sys.stderr", mock_stderr),
    ):
        setup_logging("DEBUG")

    mock_logger.remove.assert_called_once()
    assert mock_logger.add.call_count == 2

    file_call = mock_logger.add.call_args_list[0]
    assert file_call.args[0] == "logs/app.log"
    assert file_call.kwargs["level"] == "DEBUG"

    console_call = mock_logger.add.call_args_list[1]
    assert console_call.args[0] is mock_stderr
    assert console_call.kwargs["level"] == "DEBUG"


def test_setup_logging_default_level() -> None:
    with patch("src.core.logging_config.logger") as mock_logger:
        setup_logging()

    console_call = mock_logger.add.call_args_list[1]
    assert console_call.kwargs["level"] == "INFO"
