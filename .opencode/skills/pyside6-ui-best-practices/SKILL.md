---
name: pyside6-ui-best-practices
description: |
  Best practices for creating and managing Qt Designer UI files (.ui)
  and integrating them with PySide6 applications. Covers UI loading patterns,
  widget organization, layouts, signals/slots, separation of concerns,
  and testing UI components.

  Usage:
    1. In chat: "/ui-best-practices" or mention when creating PySide6 UI
    2. When designing forms, dialogs, or main windows
    3. When refactoring existing UI code
    4. When reviewing UI-related pull requests
origin: ArDEN
metadata:
  author: pay_b team
  version: "1.0.0"
  tags: [pyside6, qt-designer, ui, widgets, layouts, testing]
---

# PySide6 UI Best Practices

Universal guidelines for building maintainable PySide6 applications with Qt Designer.

## When to use this skill

- Creating new UI forms, dialogs, or windows
- Loading .ui files into Python applications
- Organizing widget hierarchies and layouts
- Implementing signal/slot connections
- Separating UI code from business logic
- Testing UI components with pytest-qt
- Code review of PySide6 code

## Quick Start

### Approach 1: Dynamic Loading (QUiLoader) - For Prototyping

```python
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import QFile

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loader = QUiLoader()
        ui_file = QFile("ui/main_window.ui")
        if not ui_file.open(QFile.ReadOnly):
            raise FileNotFoundError(f"Cannot open UI file: {ui_file.errorString()}")
        self.ui = loader.load(ui_file, self)
        ui_file.close()
        self.setCentralWidget(self.ui)
```

**Use when:** Rapid prototyping, dynamic UI changes at runtime.

### Approach 2: Compiled UI (pyside6-uic) - For Production (RECOMMENDED)

```bash
# Convert .ui to Python module
pyside6-uic ui/employee_form.ui -o ui/generated/ui_employee_form.py
```

```python
from PySide6.QtWidgets import QDialog
from ui.generated.ui_employee_form import Ui_EmployeeForm

class EmployeeForm(QDialog):
    def __init__(self):
        super().__init__()
        self.ui = Ui_EmployeeForm()
        self.ui.setupUi(self)
        # Connect signals after setupUi
        self.ui.save_button.clicked.connect(self.on_save)
```

**Use when:** Production applications, better performance, IDE autocomplete support.

## Core Principles

### 1. UI/Logic Separation

**Never mix business logic with UI code.**

```python
# BAD - Logic in UI
class EmployeeForm(QDialog):
    def save_employee(self):
        name = self.ui.name_edit.text()
        conn = sqlite3.connect("db.sqlite")  # Direct DB access!
        conn.execute("INSERT INTO employees ...")

# GOOD - Separation
class EmployeeForm(QDialog):
    def __init__(self, employee_service: EmployeeService):
        super().__init__()
        self._service = employee_service  # Dependency injection
        self.ui.save_button.clicked.connect(self.on_save)

    def on_save(self):
        data = self._collect_form_data()
        self._service.create_employee(data)  # Delegate to service
        self.accept()
```

**Pattern:** UI → Service → DAO → Database

### 2. Layout Best Practices

**Always use layouts, never fixed positions.**

```python
# BAD - Fixed positions
button.setGeometry(100, 200, 80, 30)  # Breaks on resize

# GOOD - Layouts
layout = QVBoxLayout(self)
layout.addWidget(QPushButton("Save"))
layout.addWidget(QPushButton("Cancel"))
```

**Layout selection guide:**

| Layout | Use Case |
|--------|----------|
| `QVBoxLayout` | Vertical stacking (forms, lists) |
| `QHBoxLayout` | Horizontal stacking (button rows) |
| `QGridLayout` | Grid/matrix arrangements |
| `QFormLayout` | Label-field pairs (data entry forms) |
| `QStackedLayout` | Tab-like page switching |

**Nested layouts example:**

```python
main_layout = QVBoxLayout(parent)

# Top section - form
form_layout = QFormLayout()
form_layout.addRow("Name:", name_edit)
form_layout.addRow("Rate:", rate_spinbox)
main_layout.addLayout(form_layout)

# Bottom section - buttons
button_layout = QHBoxLayout()
button_layout.addStretch()  # Push buttons to right
button_layout.addWidget(save_btn)
button_layout.addWidget(cancel_btn)
main_layout.addLayout(button_layout)
```

### 3. Widget Hierarchy

**Choose the right base class:**

```python
# QMainWindow - Full application window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setCentralWidget(central_widget)
        self.setMenuBar(self._create_menu_bar())
        self.setStatusBar(QStatusBar())

# QDialog - Modal dialogs, forms
class EmployeeForm(QDialog):
    def __init__(self):
        super().__init__()
        self.setModal(True)  # Block parent window

# QWidget - Custom components, reusable parts
class EmployeeCard(QWidget):
    def __init__(self):
        super().__init__()
        # Self-contained widget
```

### 4. Signal/Slot Patterns

**Use new-style syntax:**

```python
# Simple connection
self.ui.save_button.clicked.connect(self.on_save)

# With lambda for parameters
self.ui.load_button.clicked.connect(lambda: self.load_employee(emp_id))

# Multiple connections to same slot
self.ui.field1.textChanged.connect(self.on_form_changed)
self.ui.field2.textChanged.connect(self.on_form_changed)

# Custom signals
class DataWidget(QWidget):
    data_changed = Signal(str)  # Custom signal

    def on_change(self):
        self.data_changed.emit(self.current_data)
```

**Disconnecting signals (when needed):**

```python
# Prevent recursive updates
self.ui.field.textChanged.disconnect(self.on_field_changed)
self.ui.field.setText("new value")
self.ui.field.textChanged.connect(self.on_field_changed)
```

### 5. Resource Management

**Use .qrc files for assets:**

```xml
<!-- resources.qrc -->
<RCC>
    <qresource prefix="/icons">
        <file>icons/save.png</file>
        <file>icons/delete.png</file>
    </qresource>
</RCC>
```

```bash
# Compile resources
pyside6-rcc resources.qrc -o ui/generated/resources_rc.py
```

```python
# Use in code
from ui.generated import resources_rc  # noqa: F401
icon = QIcon(":/icons/save.png")
```

### 6. Styling with QSS

**Apply stylesheets at appropriate level:**

```python
# Application-wide (in main.py)
app.setStyleSheet("""
    QPushButton {
        padding: 8px 16px;
        border-radius: 4px;
    }
    QPushButton:hover {
        background-color: #0078d4;
        color: white;
    }
""")

# Widget-specific
self.ui.error_label.setStyleSheet("color: red; font-weight: bold;")

# Via properties (recommended for theming)
self.ui.danger_button.setProperty("class", "danger")
```

## Anti-Patterns

### Avoid These Common Mistakes

```python
# 1. Fixed sizes/positions
widget.setGeometry(100, 200, 80, 30)  # BAD
widget.setFixedSize(200, 100)          # BAD (usually)

# 2. Mixing UI and logic
def save(self):
    db = sqlite3.connect("db.sqlite")  # BAD - direct DB in UI
    db.execute(...)

# 3. Global UI state
current_form = None  # BAD - use instance variables

# 4. Loading .ui in production without caching
widget = QUiLoader().load("form.ui")  # BAD - slow in production

# 5. Blocking the main thread
def load_data(self):
    time.sleep(5)  # BAD - freezes UI
    # Use QThread or QRunnable instead

# 6. Not calling parent __init__
class MyWidget(QWidget):
    def __init__(self):
        super().setObjectName("MyWidget")  # BAD - missing super().__init__()
```

## Testing UI Components

**Basic pytest-qt setup:**

```python
# test_employee_form.py
from PySide6.QtWidgets import QApplication
from ui.employee_form import EmployeeForm

def test_form_loads(qtbot):
    """Test that form initializes correctly."""
    form = EmployeeForm()
    qtbot.addWidget(form)
    assert form.ui.name_edit is not None
    assert form.ui.save_button is not None

def test_save_button_enabled(qtbot):
    """Test save button enables when form is valid."""
    form = EmployeeForm()
    qtbot.addWidget(form)
    
    assert not form.ui.save_button.isEnabled()
    
    qtbot.keyClicks(form.ui.name_edit, "John Doe")
    assert form.ui.save_button.isEnabled()

def test_save_emits_signal(qtbot):
    """Test that save emits signal."""
    form = EmployeeForm()
    qtbot.addWidget(form)
    
    with qtbot.waitSignal(form.employee_saved) as blocker:
        qtbot.mouseClick(form.ui.save_button, Qt.LeftButton)
    
    assert blocker.args[0] == "success"
```

**Mocking external dependencies:**

```python
from unittest.mock import Mock

def test_save_calls_service(qtbot):
    """Test that save delegates to service."""
    mock_service = Mock()
    form = EmployeeForm(employee_service=mock_service)
    qtbot.addWidget(form)
    
    qtbot.keyClicks(form.ui.name_edit, "Jane Doe")
    qtbot.mouseClick(form.ui.save_button, Qt.LeftButton)
    
    mock_service.create_employee.assert_called_once()
```

## Project Structure Recommendations

```
project/
├── ui/
│   ├── forms/              # .ui files from Qt Designer
│   │   ├── main_window.ui
│   │   └── employee_form.ui
│   ├── generated/          # Compiled Python from pyside6-uic
│   │   ├── ui_main_window.py
│   │   └── ui_employee_form.py
│   ├── components/         # Custom widget classes
│   │   ├── main_window.py
│   │   └── employee_form.py
│   └── resources/          # Icons, images, styles
│       ├── icons/
│       └── styles.qss
├── services/               # Business logic
├── database/               # Data access layer
└── tests/
    └── ui/                 # UI tests
```

## References

- @references/ui-loading-patterns.md - Detailed QUiLoader vs pyside6-uic comparison
- @references/layout-examples.md - Complex layout combinations
- @references/testing-ui.md - Comprehensive pytest-qt guide

## Scripts

- @scripts/main_window_template.py - Production-ready QMainWindow template
- @scripts/dialog_template.py - QDialog template with validation
- @scripts/widget_template.py - Reusable QWidget component template

## Official Resources

- Qt for Python Documentation: https://doc.qt.io/qtforpython-6/
- Qt Designer Manual: https://doc.qt.io/qt-6/qtdesigner-manual.html
- pytest-qt: https://pytest-qt.readthedocs.io/
