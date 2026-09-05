"""Dialog Template for PySide6.

Production-ready QDialog with form validation, data binding,
and signal emission using compiled UI from pyside6-uic.

Usage:
    1. Design dialog in Qt Designer, save as employee_form.ui
    2. Compile: pyside6-uic ui/employee_form.ui -o ui/generated/ui_employee_form.py
    3. Inherit from this template and customize
"""

import logging
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QMessageBox

logger = logging.getLogger(__name__)

# Import compiled UI (uncomment after running pyside6-uic)
# from ui.generated.ui_employee_form import Ui_EmployeeForm


class EmployeeForm(QDialog):
    """Employee data entry dialog.

    Provides form validation, data binding, and signal emission
    for employee create/edit operations.

    Signals:
        employee_saved: Emitted when employee is saved successfully
        employee_deleted: Emitted when employee is deleted

    Attributes:
        ui: Compiled UI object from pyside6-uic
        _employee_id: ID of employee being edited (None for new)
    """

    employee_saved = Signal(dict)
    employee_deleted = Signal(int)

    def __init__(
        self,
        employee_id: int | None = None,
        parent=None,
    ) -> None:
        """Initialize dialog.

        Args:
            employee_id: Employee ID for edit mode (None for new)
            parent: Parent widget
        """
        super().__init__(parent)

        self._employee_id = employee_id
        self._is_dirty = False

        # Window setup
        self.setWindowTitle("Edit Employee" if employee_id else "New Employee")
        self.setModal(True)
        self.resize(400, 300)

        # Initialize UI (uncomment after compiling)
        # self.ui = Ui_EmployeeForm()
        # self.ui.setupUi(self)

        # Setup validation and signals
        self._setup_validation()
        self._connect_signals()

        # Load data if editing
        if employee_id:
            self._load_employee(employee_id)

    def _setup_validation(self) -> None:
        """Set up form validation rules."""
        # Initially disable save button
        # self.ui.save_button.setEnabled(False)

        # Connect validation triggers
        # self.ui.name_edit.textChanged.connect(self._validate_form)
        # self.ui.rate_spinbox.valueChanged.connect(self._validate_form)

    def _validate_form(self) -> None:
        """Validate form and update save button state."""
        # is_valid = (
        #     self.ui.name_edit.text().strip() != ""
        #     and self.ui.rate_spinbox.value() > 0
        # )
        # self.ui.save_button.setEnabled(is_valid)
        # self._is_dirty = True
        pass

    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        # self.ui.save_button.clicked.connect(self.on_save)
        # self.ui.cancel_button.clicked.connect(self.reject)
        # self.ui.delete_button.clicked.connect(self.on_delete)
        pass

    def _load_employee(self, employee_id: int) -> None:
        """Load employee data into form.

        Args:
            employee_id: Employee ID to load
        """
        logger.info(f"Loading employee {employee_id}")
        # Replace with actual data loading
        # employee = self._service.get_employee(employee_id)
        # self.ui.name_edit.setText(employee.name)
        # self.ui.rate_spinbox.setValue(employee.rate)
        pass

    def _collect_data(self) -> dict[str, Any]:
        """Collect form data into dictionary.

        Returns:
            Dictionary with form field values
        """
        return {
            # "name": self.ui.name_edit.text().strip(),
            # "rate": self.ui.rate_spinbox.value(),
            # "department": self.ui.department_combo.currentText(),
        }

    def on_save(self) -> None:
        """Handle save button click."""
        if not self._validate_form():
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please fill in all required fields.",
            )
            return

        try:
            data = self._collect_data()
            logger.info(f"Saving employee: {data}")

            # Replace with actual save logic
            # if self._employee_id:
            #     self._service.update_employee(self._employee_id, data)
            # else:
            #     self._service.create_employee(data)

            self.employee_saved.emit(data)
            self.accept()

        except Exception as e:
            logger.exception(f"Failed to save employee: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save employee:\n{e}",
            )

    def on_delete(self) -> None:
        """Handle delete button click."""
        if not self._employee_id:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this employee?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            try:
                logger.info(f"Deleting employee {self._employee_id}")
                # self._service.delete_employee(self._employee_id)
                self.employee_deleted.emit(self._employee_id)
                self.accept()

            except Exception as e:
                logger.exception(f"Failed to delete employee: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to delete employee:\n{e}",
                )

    def get_data(self) -> dict[str, Any]:
        """Get current form data.

        Returns:
            Dictionary with current form values
        """
        return self._collect_data()

    def set_data(self, data: dict[str, Any]) -> None:
        """Populate form from dictionary.

        Args:
            data: Dictionary with field values
        """
        # self.ui.name_edit.setText(data.get("name", ""))
        # self.ui.rate_spinbox.setValue(data.get("rate", 0))
        # self.ui.department_combo.setCurrentText(data.get("department", ""))
        pass


# Example usage
if __name__ == "__main__":
    import sys

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # New employee
    dialog = EmployeeForm()
    if dialog.exec() == QDialog.Accepted:
        print(f"Saved: {dialog.get_data()}")

    # Edit employee
    dialog = EmployeeForm(employee_id=1)
    if dialog.exec() == QDialog.Accepted:
        print(f"Updated: {dialog.get_data()}")
