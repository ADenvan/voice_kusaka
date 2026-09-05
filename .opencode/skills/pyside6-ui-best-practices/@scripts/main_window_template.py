"""Main Window Template for PySide6.

Production-ready QMainWindow with menu bar, toolbar, status bar,
and central widget using compiled UI from pyside6-uic.

Usage:
    1. Design UI in Qt Designer, save as main_window.ui
    2. Compile: pyside6-uic ui/main_window.ui -o ui/generated/ui_main_window.py
    3. Inherit from this template and customize
"""

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QToolBar,
)

logger = logging.getLogger(__name__)

# Import compiled UI (uncomment after running pyside6-uic)
# from ui.generated.ui_main_window import Ui_MainWindow


class MainWindow(QMainWindow):
    """Main application window.

    Provides standard window chrome: menu bar, toolbar,
    status bar, and central widget area.

    Attributes:
        ui: Compiled UI object from pyside6-uic
        _settings: QSettings for window state persistence
    """

    def __init__(self) -> None:
        """Initialize main window."""
        super().__init__()

        # Window setup
        self.setWindowTitle("Application")
        self.resize(1024, 768)

        # Initialize UI (uncomment after compiling)
        # self.ui = Ui_MainWindow()
        # self.ui.setupUi(self)

        # Settings for state persistence
        self._settings = QSettings("MyCompany", "MyApp")

        # Build UI components
        self._create_menu_bar()
        self._create_tool_bar()
        self._create_status_bar()
        self._create_central_widget()
        self._connect_signals()

        # Restore state
        self._restore_state()

    def _create_menu_bar(self) -> None:
        """Create application menu bar."""
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")

        self._action_new = QAction("&New", self)
        self._action_new.setShortcut("Ctrl+N")
        self._action_new.setStatusTip("Create new")
        file_menu.addAction(self._action_new)

        self._action_open = QAction("&Open...", self)
        self._action_open.setShortcut("Ctrl+O")
        self._action_open.setStatusTip("Open file")
        file_menu.addAction(self._action_open)

        file_menu.addSeparator()

        self._action_exit = QAction("E&xit", self)
        self._action_exit.setShortcut("Ctrl+Q")
        self._action_exit.setStatusTip("Exit application")
        self._action_exit.triggered.connect(self.close)
        file_menu.addAction(self._action_exit)

        # Edit menu
        edit_menu = menu_bar.addMenu("&Edit")

        self._action_undo = QAction("&Undo", self)
        self._action_undo.setShortcut("Ctrl+Z")
        edit_menu.addAction(self._action_undo)

        self._action_redo = QAction("&Redo", self)
        self._action_redo.setShortcut("Ctrl+Y")
        edit_menu.addAction(self._action_redo)

        # Help menu
        help_menu = menu_bar.addMenu("&Help")

        self._action_about = QAction("&About", self)
        self._action_about.triggered.connect(self._show_about)
        help_menu.addAction(self._action_about)

    def _create_tool_bar(self) -> None:
        """Create application toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Add actions to toolbar
        toolbar.addAction(self._action_new)
        toolbar.addAction(self._action_open)
        toolbar.addSeparator()
        toolbar.addAction(self._action_undo)
        toolbar.addAction(self._action_redo)

    def _create_status_bar(self) -> None:
        """Create status bar."""
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready")

    def _create_central_widget(self) -> None:
        """Create central widget area."""
        from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.addWidget(QLabel("Main Content Area"))
        layout.setAlignment(Qt.AlignCenter)

    def _connect_signals(self) -> None:
        """Connect widget signals to slots."""
        self._action_new.triggered.connect(self._on_new)
        self._action_open.triggered.connect(self._on_open)

    def _restore_state(self) -> None:
        """Restore window geometry and state."""
        geometry = self._settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        window_state = self._settings.value("windowState")
        if window_state:
            self.restoreState(window_state)

    def _save_state(self) -> None:
        """Save window geometry and state."""
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("windowState", self.saveState())

    def _on_new(self) -> None:
        """Handle new action."""
        logger.info("New action triggered")
        self._status_bar.showMessage("New created")

    def _on_open(self) -> None:
        """Handle open action."""
        logger.info("Open action triggered")
        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            "",
            "All Files (*)",
        )
        if file_path:
            logger.info(f"Opened file: {file_path}")
            self._status_bar.showMessage(f"Opened: {Path(file_path).name}")

    def _show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About",
            "<h2>Application</h2><p>Version 1.0.0</p><p>Built with PySide6</p>",
        )

    def closeEvent(self, event) -> None:
        """Handle window close event."""
        self._save_state()
        logger.info("Application closing")
        event.accept()


def main() -> int:
    """Application entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    app = QApplication(sys.argv)
    app.setApplicationName("MyApp")
    app.setOrganizationName("MyCompany")

    # Optional: Apply stylesheet
    # app.setStyleSheet(STYLESHEET)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
