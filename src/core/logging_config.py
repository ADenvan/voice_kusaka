import sys

from loguru import logger


def setup_logging(level: str = "INFO") -> None:
    """Configure loguru logging with file and console handlers."""
    logger.remove()

    log_format = "{time:YYYY-MM-DD HH:mm:ss} | {name} | {level} | {message}"

    logger.add(
        "logs/app.log",
        rotation="10 MB",
        retention=5,
        encoding="utf-8",
        level="DEBUG",
        format=log_format,
    )

    logger.add(
        sys.stderr,
        level=level.upper(),
        format=log_format,
    )
