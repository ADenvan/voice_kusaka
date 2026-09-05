#!/usr/bin/env python3
"""Production-ready Python project template.

This template demonstrates best practices for:
- Project structure
- Type hints
- Error handling
- Logging
- Documentation
- Testing

Usage:
    1. Copy this file as your main module
    2. Rename classes and functions to match your needs
    3. Update docstrings and type hints
    4. Add your business logic
"""

from __future__ import annotations

import logging
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Generic, TypeVar

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================


class LogLevel(Enum):
    """Logging levels."""

    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


@dataclass(frozen=True)
class Config:
    """Application configuration.

    Attributes:
        app_name: Application name
        version: Application version
        debug: Debug mode flag
        log_level: Logging level
        output_dir: Output directory path
    """

    app_name: str = "MyApp"
    version: str = "1.0.0"
    debug: bool = False
    log_level: LogLevel = LogLevel.INFO
    output_dir: Path = field(default_factory=lambda: Path("./output"))

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.output_dir is None:
            object.__setattr__(self, "output_dir", Path("./output"))


# ============================================================================
# Exceptions
# ============================================================================


class ApplicationError(Exception):
    """Base exception for the application."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(ApplicationError):
    """Raised when validation fails."""

    pass


class ProcessingError(ApplicationError):
    """Raised when processing fails."""

    pass


class NotFoundError(ApplicationError):
    """Raised when a resource is not found."""

    pass


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class DataItem:
    """Represents a data item.

    Attributes:
        id: Unique identifier
        name: Item name
        value: Item value
        created_at: Creation timestamp
        metadata: Optional metadata dictionary
    """

    id: int
    name: str
    value: float
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate data after initialization."""
        if not self.name:
            raise ValidationError("Name cannot be empty", {"field": "name"})
        if self.value < 0:
            raise ValidationError(
                "Value cannot be negative", {"field": "value", "value": self.value}
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "value": self.value,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DataItem:
        """Create instance from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            value=data["value"],
            created_at=datetime.fromisoformat(data["created_at"]),
            metadata=data.get("metadata", {}),
        )


# ============================================================================
# Repository Pattern
# ============================================================================

T = TypeVar("T")


class Repository(ABC, Generic[T]):
    """Abstract base class for repositories."""

    @abstractmethod
    def get_by_id(self, item_id: int) -> T | None:
        """Get item by ID.

        Args:
            item_id: Item identifier

        Returns:
            Item if found, None otherwise
        """
        pass

    @abstractmethod
    def get_all(self) -> list[T]:
        """Get all items.

        Returns:
            List of all items
        """
        pass

    @abstractmethod
    def save(self, item: T) -> None:
        """Save an item.

        Args:
            item: Item to save
        """
        pass

    @abstractmethod
    def delete(self, item_id: int) -> bool:
        """Delete an item.

        Args:
            item_id: Item identifier

        Returns:
            True if deleted, False if not found
        """
        pass


class InMemoryRepository(Repository[DataItem]):
    """In-memory implementation of DataItem repository."""

    def __init__(self) -> None:
        """Initialize repository."""
        self._items: dict[int, DataItem] = {}
        self._next_id: int = 1
        logger.debug("Initialized InMemoryRepository")

    def get_by_id(self, item_id: int) -> DataItem | None:
        """Get item by ID."""
        item = self._items.get(item_id)
        if item is None:
            logger.warning(f"Item {item_id} not found")
        return item

    def get_all(self) -> list[DataItem]:
        """Get all items."""
        return list(self._items.values())

    def save(self, item: DataItem) -> None:
        """Save an item."""
        if item.id == 0:
            item.id = self._next_id
            self._next_id += 1
            logger.info(f"Created new item with ID {item.id}")
        else:
            logger.info(f"Updated item {item.id}")

        self._items[item.id] = item

    def delete(self, item_id: int) -> bool:
        """Delete an item."""
        if item_id in self._items:
            del self._items[item_id]
            logger.info(f"Deleted item {item_id}")
            return True
        logger.warning(f"Cannot delete: item {item_id} not found")
        return False

    def clear(self) -> None:
        """Clear all items."""
        self._items.clear()
        self._next_id = 1
        logger.info("Repository cleared")


# ============================================================================
# Service Layer
# ============================================================================


class DataService:
    """Business logic for data operations."""

    def __init__(self, repository: Repository[DataItem]) -> None:
        """Initialize service with repository.

        Args:
            repository: Data repository
        """
        self._repository = repository
        logger.debug("Initialized DataService")

    def create_item(self, name: str, value: float, **metadata: Any) -> DataItem:
        """Create a new data item.

        Args:
            name: Item name
            value: Item value
            **metadata: Optional metadata

        Returns:
            Created data item

        Raises:
            ValidationError: If validation fails
            ProcessingError: If creation fails
        """
        try:
            item = DataItem(
                id=0,
                name=name,
                value=value,
                metadata=metadata,
            )
            self._repository.save(item)
            logger.info(f"Created item: {item}")
            return item
        except ValidationError:
            raise
        except Exception as e:
            logger.exception("Failed to create item")
            raise ProcessingError(f"Creation failed: {e}") from e

    def get_item(self, item_id: int) -> DataItem:
        """Get item by ID.

        Args:
            item_id: Item identifier

        Returns:
            Data item

        Raises:
            NotFoundError: If item not found
        """
        item = self._repository.get_by_id(item_id)
        if item is None:
            raise NotFoundError("Item", str(item_id))
        return item

    def list_items(self, min_value: float | None = None) -> list[DataItem]:
        """List all items, optionally filtered.

        Args:
            min_value: Minimum value filter

        Returns:
            List of items
        """
        items = self._repository.get_all()

        if min_value is not None:
            items = [item for item in items if item.value >= min_value]

        logger.debug(f"Listed {len(items)} items")
        return items

    def process_items(self, processor: callable) -> list[Any]:
        """Process all items with a function.

        Args:
            processor: Function to process each item

        Returns:
            List of processing results
        """
        items = self._repository.get_all()
        results = []

        for item in items:
            try:
                result = processor(item)
                results.append(result)
                logger.debug(f"Processed item {item.id}")
            except Exception as e:
                logger.warning(f"Failed to process item {item.id}: {e}")
                continue

        logger.info(f"Processed {len(results)}/{len(items)} items")
        return results


# ============================================================================
# Main Application
# ============================================================================


class Application:
    """Main application class."""

    def __init__(self, config: Config) -> None:
        """Initialize application.

        Args:
            config: Application configuration
        """
        self._config = config
        self._setup_logging()

        # Initialize components
        self._repository = InMemoryRepository()
        self._service = DataService(self._repository)

        logger.info(f"Initialized {config.app_name} v{config.version}")

    def _setup_logging(self) -> None:
        """Configure logging."""
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        if self._config.debug:
            logging.basicConfig(
                level=logging.DEBUG,
                format=log_format,
                handlers=[
                    logging.StreamHandler(sys.stdout),
                ],
            )
        else:
            logging.basicConfig(
                level=self._config.log_level.value,
                format=log_format,
                handlers=[
                    logging.StreamHandler(sys.stdout),
                ],
            )

    def run(self) -> int:
        """Run the application.

        Returns:
            Exit code (0 for success)
        """
        try:
            logger.info("Starting application")

            # Create some sample data
            logger.info("Creating sample data...")
            item1 = self._service.create_item("First Item", 100.0, category="test", priority="high")
            item2 = self._service.create_item("Second Item", 50.0, category="test", priority="low")
            item3 = self._service.create_item("Third Item", 200.0, category="production")

            # List all items
            logger.info("Listing all items:")
            all_items = self._service.list_items()
            for item in all_items:
                logger.info(f"  - {item.name}: {item.value}")

            # List items with filter
            logger.info("Items with value >= 100:")
            filtered_items = self._service.list_items(min_value=100.0)
            for item in filtered_items:
                logger.info(f"  - {item.name}: {item.value}")

            # Get specific item
            retrieved = self._service.get_item(item1.id)
            logger.info(f"Retrieved: {retrieved}")

            # Process items
            logger.info("Processing items:")
            results = self._service.process_items(lambda item: f"Processed: {item.name}")
            for result in results:
                logger.info(f"  {result}")

            logger.info("Application completed successfully")
            return 0

        except NotFoundError as e:
            logger.error(f"Not found: {e.message}")
            return 1
        except ValidationError as e:
            logger.error(f"Validation error: {e.message}")
            if e.details:
                logger.error(f"Details: {e.details}")
            return 1
        except ApplicationError as e:
            logger.error(f"Application error: {e.message}")
            return 1
        except Exception:
            logger.exception("Unexpected error")
            return 1


# ============================================================================
# CLI Entry Point
# ============================================================================


def create_parser() -> Any:
    """Create argument parser.

    Returns:
        Argument parser
    """
    try:
        import argparse

        parser = argparse.ArgumentParser(
            description="Application description",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
    %(prog)s                          # Run with defaults
    %(prog)s --debug                  # Run in debug mode
    %(prog)s --log-level DEBUG        # Set log level
            """,
        )

        parser.add_argument(
            "--version",
            action="version",
            version="%(prog)s 1.0.0",
        )

        parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable debug mode",
        )

        parser.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            default="INFO",
            help="Set logging level (default: INFO)",
        )

        parser.add_argument(
            "--output",
            type=str,
            default="./output",
            help="Output directory (default: ./output)",
        )

        return parser

    except ImportError:
        return None


def main(argv: list[str] | None = None) -> int:
    """Main entry point.

    Args:
        argv: Command-line arguments

    Returns:
        Exit code
    """
    parser = create_parser()

    if parser:
        args = parser.parse_args(argv)

        config = Config(
            debug=args.debug,
            log_level=LogLevel[args.log_level],
            output_dir=Path(args.output),
        )
    else:
        # Fallback if argparse not available
        config = Config()

    app = Application(config)
    return app.run()


# ============================================================================
# Module Entry Point
# ============================================================================

if __name__ == "__main__":
    sys.exit(main())
