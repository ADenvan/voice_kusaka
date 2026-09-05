# Testing UI Components with pytest-qt

Comprehensive guide for testing PySide6 applications using pytest-qt.

## Setup

### Installation

```bash
pip install pytest pytest-qt
```

### Basic Configuration

```python
# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
addopts = "--tb=short -v"
```

### Conftest Setup

```python
# tests/ui/conftest.py
import pytest
from PySide6.QtWidgets import QApplication

@pytest.fixture(autouse=True)
def app():
    """Ensure QApplication exists for all UI tests."""
    if not QApplication.instance():
        app = QApplication([])
    else:
        app = QApplication.instance()
    return app
```

## Basic Testing Patterns

### Test Widget Initialization

```python
from PySide6.QtWidgets import QDialog
from ui.components.employee_form import EmployeeForm

def test_form_initializes(qtbot):
    """Test that form loads without errors."""
    form = EmployeeForm()
    qtbot.addWidget(form)  # Ensures cleanup
    
    assert form.ui.name_edit is not None
    assert form.ui.save_button is not None
    assert form.ui.cancel_button is not None
```

### Test Widget Properties

```python
def test_form_widgets_have_correct_properties(qtbot):
    """Test initial widget state."""
    form = EmployeeForm()
    qtbot.addWidget(form)
    
    # Text fields
    assert form.ui.name_edit.text() == ""
    assert form.ui.name_edit.placeholderText() == "Enter name"
    
    # Buttons
    assert form.ui.save_button.text() == "Save"
    assert not form.ui.save_button.isEnabled()  # Disabled until valid input
    
    # Spinbox
    assert form.ui.rate_spinbox.minimum() == 0
    assert form.ui.rate_spinbox.maximum() == 999999
```

### Test User Interactions

```python
from PySide6.QtCore import Qt

def test_typing_in_name_field(qtbot):
    """Test that typing updates field value."""
    form = EmployeeForm()
    qtbot.addWidget(form)
    
    # Type text
    qtbot.keyClicks(form.ui.name_edit, "John Doe")
    
    assert form.ui.name_edit.text() == "John Doe"

def test_clicking_save_button(qtbot):
    """Test save button click."""
    form = EmployeeForm()
    qtbot.addWidget(form)
    
    # Fill form first
    qtbot.keyClicks(form.ui.name_edit, "Jane Doe")
    form.ui.rate_spinbox.setValue(50)
    
    # Click save
    qtbot.mouseClick(form.ui.save_button, Qt.LeftButton)
    
    # Verify action (dialog accepted, signal emitted, etc.)
    assert form.result() == QDialog.Accepted
```

## Testing Signals

### Wait for Signal

```python
def test_employee_saved_signal(qtbot):
    """Test that save emits signal with correct data."""
    form = EmployeeForm()
    qtbot.addWidget(form)
    
    # Fill form
    qtbot.keyClicks(form.ui.name_edit, "Test Employee")
    form.ui.rate_spinbox.setValue(75)
    
    # Wait for signal
    with qtbot.waitSignal(form.employee_saved, timeout=1000) as blocker:
        qtbot.mouseClick(form.ui.save_button, Qt.LeftButton)
    
    # Verify signal args
    assert blocker.args[0] == "success"

def test_signal_with_multiple_args(qtbot):
    """Test signal with multiple arguments."""
    with qtbot.waitSignal(widget.data_changed, timeout=500) as blocker:
        widget.set_data({"name": "Test", "rate": 50})
    
    name, rate = blocker.args
    assert name == "Test"
    assert rate == 50
```

### Verify Signal Not Emitted

```python
def test_invalid_form_does_not_emit_signal(qtbot):
    """Test that invalid form doesn't emit save signal."""
    form = EmployeeForm()
    qtbot.addWidget(form)
    
    # Don't fill form (invalid state)
    with qtbot.assert_not_emitted(form.employee_saved):
        qtbot.mouseClick(form.ui.save_button, Qt.LeftButton)
```

## Mocking Dependencies

### Mock Service Layer

```python
from unittest.mock import Mock, patch

def test_save_calls_service(qtbot):
    """Test that save delegates to service."""
    mock_service = Mock()
    form = EmployeeForm(employee_service=mock_service)
    qtbot.addWidget(form)
    
    # Fill form
    qtbot.keyClicks(form.ui.name_edit, "John")
    form.ui.rate_spinbox.setValue(100)
    
    # Click save
    qtbot.mouseClick(form.ui.save_button, Qt.LeftButton)
    
    # Verify service was called
    mock_service.create_employee.assert_called_once()
    call_args = mock_service.create_employee.call_args[0][0]
    assert call_args["name"] == "John"
    assert call_args["rate"] == 100

def test_load_populates_form(qtbot):
    """Test that loading data populates form fields."""
    mock_service = Mock()
    mock_service.get_employee.return_value = {
        "name": "Existing Employee",
        "rate": 85
    }
    
    form = EmployeeForm(employee_service=mock_service)
    qtbot.addWidget(form)
    
    # Trigger load
    form.load_employee(1)
    
    assert form.ui.name_edit.text() == "Existing Employee"
    assert form.ui.rate_spinbox.value() == 85
```

### Patch External Calls

```python
@patch("ui.components.employee_form.QMessageBox")
def test_error_shows_dialog(mock_message_box, qtbot):
    """Test that errors show message box."""
    mock_service = Mock()
    mock_service.create_employee.side_effect = Exception("DB error")
    
    form = EmployeeForm(employee_service=mock_service)
    qtbot.addWidget(form)
    
    # Fill and save
    qtbot.keyClicks(form.ui.name_edit, "Test")
    form.ui.rate_spinbox.setValue(50)
    qtbot.mouseClick(form.ui.save_button, Qt.LeftButton)
    
    # Verify error dialog shown
    mock_message_box.critical.assert_called_once()
```

## Testing Validation

### Form Validation

```python
def test_save_button_disabled_when_empty(qtbot):
    """Test save button is disabled with empty form."""
    form = EmployeeForm()
    qtbot.addWidget(form)
    
    assert not form.ui.save_button.isEnabled()

def test_save_button_enabled_when_valid(qtbot):
    """Test save button enables when form is valid."""
    form = EmployeeForm()
    qtbot.addWidget(form)
    
    qtbot.keyClicks(form.ui.name_edit, "Valid Name")
    form.ui.rate_spinbox.setValue(50)
    
    assert form.ui.save_button.isEnabled()

def test_validation_on_change(qtbot):
    """Test validation updates on field change."""
    form = EmployeeForm()
    qtbot.addWidget(form)
    
    # Initially invalid
    assert not form.ui.save_button.isEnabled()
    
    # Make valid
    qtbot.keyClicks(form.ui.name_edit, "Name")
    assert form.ui.save_button.isEnabled()
    
    # Make invalid again
    qtbot.keyClicks(form.ui.name_edit, "")  # Clear field
    assert not form.ui.save_button.isEnabled()
```

## Testing Dialogs

### Modal Dialog Behavior

```python
def test_dialog_is_modal(qtbot):
    """Test that dialog blocks parent."""
    form = EmployeeForm()
    qtbot.addWidget(form)
    
    assert form.isModal()
    assert form.windowModality() == Qt.WindowModal

def test_accept_closes_dialog(qtbot):
    """Test that accept() closes dialog."""
    form = EmployeeForm()
    qtbot.addWidget(form)
    
    with qtbot.waitSignal(form.finished):
        form.accept()
    
    assert not form.isVisible()

def test_reject_closes_dialog(qtbot):
    """Test that reject() closes dialog."""
    form = EmployeeForm()
    qtbot.addWidget(form)
    
    with qtbot.waitSignal(form.finished):
        form.reject()
    
    assert not form.isVisible()
```

## Testing QMainWindow

### Menu Actions

```python
def test_menu_action_triggers_function(qtbot):
    """Test that menu action triggers expected function."""
    window = MainWindow()
    qtbot.addWidget(window)
    
    # Trigger action directly
    window.ui.actionExit.trigger()
    
    # Verify window closed or action performed
    assert not window.isVisible()

def test_toolbar_buttons(qtbot):
    """Test toolbar button clicks."""
    window = MainWindow()
    qtbot.addWidget(window)
    
    qtbot.mouseClick(window.ui.refresh_button, Qt.LeftButton)
    
    # Verify refresh happened
    assert window.ui.status_label.text() == "Refreshed"
```

## Testing Custom Widgets

### Widget Behavior

```python
def test_custom_spinbox_validation(qtbot):
    """Test custom widget validation."""
    from ui.components.custom_spinbox import CustomSpinBox
    
    spinbox = CustomSpinBox()
    qtbot.addWidget(spinbox)
    
    spinbox.setValue(100)
    assert spinbox.validate_input()
    
    spinbox.setValue(0)
    assert not spinbox.validate_input()

def test_widget_signals(qtbot):
    """Test custom widget emits signals."""
    widget = CustomWidget()
    qtbot.addWidget(widget)
    
    with qtbot.waitSignal(widget.value_changed, timeout=500):
        widget.set_value(42)
```

## Advanced Patterns

### Parametrized Tests

```python
import pytest

@pytest.mark.parametrize("name,rate,expected_valid", [
    ("John", 50, True),
    ("", 50, False),      # Empty name
    ("John", 0, False),   # Zero rate
    ("John", -1, False),  # Negative rate
])
def test_form_validation(qtbot, name, rate, expected_valid):
    """Test various validation scenarios."""
    form = EmployeeForm()
    qtbot.addWidget(form)
    
    qtbot.keyClicks(form.ui.name_edit, name)
    form.ui.rate_spinbox.setValue(rate)
    
    assert form.ui.save_button.isEnabled() == expected_valid
```

### Async Operations

```python
import asyncio

def test_async_load(qtbot):
    """Test async data loading."""
    form = EmployeeForm()
    qtbot.addWidget(form)
    
    # Start async load
    form.load_employee_async(1)
    
    # Wait for completion signal
    with qtbot.waitSignal(form.employee_loaded, timeout=5000) as blocker:
        pass
    
    # Verify loaded data
    assert blocker.args[0]["name"] == "Test Employee"
```

### Screenshot Testing

```python
def test_form_appearance(qtbot, tmp_path):
    """Test form visual appearance."""
    form = EmployeeForm()
    qtbot.addWidget(form)
    form.resize(400, 300)
    form.show()
    
    # Take screenshot
    screenshot = form.grab()
    screenshot.save(str(tmp_path / "form.png"))
    
    # Compare with baseline (requires additional setup)
    # assert screenshots_match(tmp_path / "form.png", baseline_path)
```

## Best Practices

1. **Always use qtbot.addWidget()** - Ensures proper cleanup
2. **Set timeouts explicitly** - `timeout=1000` for waitSignal
3. **Mock external dependencies** - Don't test DB/network in UI tests
4. **Test user interactions** - Use keyClicks, mouseClick
5. **Test signals** - Verify emit patterns
6. **Use parametrization** - Test multiple scenarios
7. **Keep tests isolated** - Each test creates fresh widgets
8. **Test validation** - Both valid and invalid states

## Common Pitfalls

```python
# BAD - No qtbot.addWidget (memory leak)
def test_bad(qtbot):
    form = EmployeeForm()
    # Missing: qtbot.addWidget(form)

# BAD - Testing implementation details
def test_too_detailed(qtbot):
    form = EmployeeForm()
    qtbot.addWidget(form)
    # Don't test internal _validate_form method
    # Test observable behavior instead

# BAD - No timeout (hangs forever if signal not emitted)
def test_no_timeout(qtbot):
    with qtbot.waitSignal(form.employee_saved):  # No timeout!
        form.save()

# GOOD - Proper test
def test_good(qtbot):
    form = EmployeeForm()
    qtbot.addWidget(form)
    
    with qtbot.waitSignal(form.employee_saved, timeout=1000):
        qtbot.mouseClick(form.ui.save_button, Qt.LeftButton)
```

## Running Tests

```bash
# Run all UI tests
pytest tests/ui/ -v

# Run with coverage
pytest tests/ui/ --cov=ui --cov-report=html

# Run specific test
pytest tests/ui/test_employee_form.py::test_form_initializes -v

# Run with GUI visible (for debugging)
pytest tests/ui/ --show
```
