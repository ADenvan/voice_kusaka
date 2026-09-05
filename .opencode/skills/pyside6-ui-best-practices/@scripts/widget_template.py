"""Custom Widget Template for PySide6.

Production-ready QWidget for creating reusable custom components
with signals, properties, and styling support.

Usage:
    1. Design widget in Qt Designer (optional)
    2. Compile if using UI: pyside6-uic ui/custom_widget.ui -o ui/generated/ui_custom_widget.py
    3. Inherit from this template and customize
"""

import logging
from typing import Any

from PySide6.QtCore import Property, Signal, Slot
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class CustomWidget(QWidget):
    """Reusable custom widget component.

    Demonstrates custom signals, properties, and slots
    for creating self-contained, reusable widgets.

    Signals:
        value_changed: Emitted when widget value changes
        clicked: Emitted when widget is clicked
        data_ready: Emitted when data is loaded/processed

    Properties:
        value: Current widget value (int)
        label: Display label text (str)
        enabled: Widget enabled state (bool)
    """

    # Custom signals
    value_changed = Signal(int)
    clicked = Signal()
    data_ready = Signal(dict)

    def __init__(
        self,
        initial_value: int = 0,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize custom widget.

        Args:
            initial_value: Initial value for the widget
            parent: Parent widget
        """
        super().__init__(parent)

        self._value = initial_value
        self._label_text = "Custom Widget"
        self._is_enabled = True

        # Setup UI
        self._setup_ui()
        self._connect_signals()

        # Apply initial state
        self._update_display()

    def _setup_ui(self) -> None:
        """Create widget layout and components."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Label section
        self._label = QLabel(self._label_text)
        self._label.setObjectName("widget_label")
        main_layout.addWidget(self._label)

        # Value display
        self._value_label = QLabel(str(self._value))
        self._value_label.setObjectName("value_label")
        self._value_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #0078d4;")
        main_layout.addWidget(self._value_label)

        # Button row
        button_layout = QHBoxLayout()

        self._decrement_btn = QPushButton("-")
        self._decrement_btn.setObjectName("decrement_button")
        self._decrement_btn.setFixedSize(40, 40)
        button_layout.addWidget(self._decrement_btn)

        button_layout.addStretch()

        self._increment_btn = QPushButton("+")
        self._increment_btn.setObjectName("increment_button")
        self._increment_btn.setFixedSize(40, 40)
        button_layout.addWidget(self._increment_btn)

        main_layout.addLayout(button_layout)

    def _connect_signals(self) -> None:
        """Connect internal widget signals."""
        self._increment_btn.clicked.connect(self._on_increment)
        self._decrement_btn.clicked.connect(self._on_decrement)

    def _on_increment(self) -> None:
        """Handle increment button click."""
        self.value = self._value + 1

    def _on_decrement(self) -> None:
        """Handle decrement button click."""
        self.value = self._value - 1

    def _update_display(self) -> None:
        """Update visual display to match internal state."""
        self._value_label.setText(str(self._value))
        self._label.setText(self._label_text)

        # Update enabled state
        self._increment_btn.setEnabled(self._is_enabled)
        self._decrement_btn.setEnabled(self._is_enabled)

    # --- Properties ---

    def _get_value(self) -> int:
        """Get current value."""
        return self._value

    def _set_value(self, value: int) -> None:
        """Set value and emit signal if changed."""
        if self._value != value:
            self._value = value
            self._update_display()
            self.value_changed.emit(self._value)
            logger.debug(f"Value changed to {self._value}")

    value = Property(int, _get_value, _set_value, notify=value_changed)

    def _get_label(self) -> str:
        """Get label text."""
        return self._label_text

    def _set_label(self, text: str) -> None:
        """Set label text."""
        if self._label_text != text:
            self._label_text = text
            self._update_display()

    label = Property(str, _get_label, _set_label)

    def _get_enabled(self) -> bool:
        """Get enabled state."""
        return self._is_enabled

    def _set_enabled(self, enabled: bool) -> None:
        """Set enabled state."""
        if self._is_enabled != enabled:
            self._is_enabled = enabled
            self._update_display()
            super().setEnabled(enabled)

    enabled = Property(bool, _get_enabled, _set_enabled)

    # --- Public API ---

    @Slot()
    def reset(self) -> None:
        """Reset widget to initial state."""
        self.value = 0
        logger.info("Widget reset")

    @Slot(dict)
    def load_data(self, data: dict[str, Any]) -> None:
        """Load data into widget.

        Args:
            data: Dictionary with widget data
        """
        logger.info(f"Loading data: {data}")
        self.value = data.get("value", 0)
        self.label = data.get("label", "Custom Widget")
        self.data_ready.emit(data)

    @Slot()
    def click(self) -> None:
        """Programmatically trigger click."""
        self.clicked.emit()

    def get_data(self) -> dict[str, Any]:
        """Get current widget data.

        Returns:
            Dictionary with current widget state
        """
        return {
            "value": self._value,
            "label": self._label_text,
            "enabled": self._is_enabled,
        }

    def set_data(self, data: dict[str, Any]) -> None:
        """Set widget data from dictionary.

        Args:
            data: Dictionary with widget state
        """
        self.value = data.get("value", 0)
        self.label = data.get("label", "Custom Widget")
        self.enabled = data.get("enabled", True)


# Example usage
if __name__ == "__main__":
    import sys

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    widget = CustomWidget(initial_value=10)
    widget.setWindowTitle("Custom Widget Demo")
    widget.resize(300, 200)

    # Connect to signals
    widget.value_changed.connect(lambda v: print(f"Value: {v}"))
    widget.clicked.connect(lambda: print("Clicked!"))
    widget.data_ready.connect(lambda d: print(f"Data: {d}"))

    widget.show()
    sys.exit(app.exec())
