# UI Loading Patterns: QUiLoader vs pyside6-uic

Detailed comparison of approaches for loading Qt Designer .ui files in PySide6.

## Overview

Qt Designer saves UI designs as XML `.ui` files. PySide6 provides two ways to use them:

1. **QUiLoader** - Dynamic loading at runtime
2. **pyside6-uic** - Compile to Python code

## Approach 1: QUiLoader (Dynamic Loading)

### How It Works

```python
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile

loader = QUiLoader()
ui_file = QFile("path/to/form.ui")
ui_file.open(QFile.ReadOnly)
widget = loader.load(ui_file, parent)
ui_file.close()
```

### Complete Example

```python
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow, QApplication
from PySide6.QtCore import QFile
import sys

class DynamicUIWindow(QMainWindow):
    def __init__(self, ui_path: str):
        super().__init__()
        self._load_ui(ui_path)
        self._connect_signals()
    
    def _load_ui(self, ui_path: str) -> None:
        """Load UI file dynamically."""
        loader = QUiLoader()
        ui_file = QFile(ui_path)
        
        if not ui_file.open(QFile.ReadOnly):
            raise FileNotFoundError(f"Cannot open {ui_path}: {ui_file.errorString()}")
        
        self.ui = loader.load(ui_file, self)
        ui_file.close()
        
        if self.ui is None:
            raise RuntimeError(f"Failed to load UI: {loader.errorString()}")
    
    def _connect_signals(self) -> None:
        """Connect widget signals to slots."""
        # Access widgets via self.ui
        self.ui.save_button.clicked.connect(self.on_save)
        self.ui.cancel_button.clicked.connect(self.on_cancel)
    
    def on_save(self) -> None:
        print("Save clicked")
    
    def on_cancel(self) -> None:
        print("Cancel clicked")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DynamicUIWindow("ui/form.ui")
    window.show()
    sys.exit(app.exec())
```

### Pros

- No compilation step needed
- UI changes reflected immediately
- Good for rapid prototyping
- Can load different UI files at runtime

### Cons

- Slower (parses XML at runtime)
- No IDE autocomplete for UI elements
- No type hints for widgets
- Harder to debug typos in widget names
- Cannot promote custom widgets easily

### When to Use

- Prototyping and experimentation
- Applications with dynamic UI themes
- Development phase for quick iteration

## Approach 2: pyside6-uic (Compiled)

### How It Works

```bash
# Convert .ui to Python
pyside6-uic ui/form.ui -o ui/generated/ui_form.py
```

```python
from ui.generated.ui_form import Ui_Form

class MyForm(QDialog):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)
```

### Complete Example

```python
# ui/components/employee_form.py
from PySide6.QtWidgets import QDialog
from PySide6.QtCore import Signal
from ui.generated.ui_employee_form import Ui_EmployeeForm

class EmployeeForm(QDialog):
    """Employee data entry form."""
    
    employee_saved = Signal(str)  # Custom signal
    
    def __init__(self):
        super().__init__()
        self.ui = Ui_EmployeeForm()
        self.ui.setupUi(self)
        self._setup_validation()
        self._connect_signals()
    
    def _setup_validation(self) -> None:
        """Set up form validation."""
        self.ui.name_edit.textChanged.connect(self._validate_form)
        self.ui.rate_spinbox.valueChanged.connect(self._validate_form)
        self.ui.save_button.setEnabled(False)
    
    def _validate_form(self) -> None:
        """Enable save button when form is valid."""
        is_valid = (
            self.ui.name_edit.text().strip() != ""
            and self.ui.rate_spinbox.value() > 0
        )
        self.ui.save_button.setEnabled(is_valid)
    
    def _connect_signals(self) -> None:
        """Connect UI signals."""
        self.ui.save_button.clicked.connect(self.on_save)
        self.ui.cancel_button.clicked.connect(self.reject)
    
    def on_save(self) -> None:
        """Handle save button click."""
        data = {
            "name": self.ui.name_edit.text().strip(),
            "rate": self.ui.rate_spinbox.value(),
        }
        # Process data...
        self.employee_saved.emit("success")
        self.accept()
    
    def get_data(self) -> dict:
        """Get form data as dictionary."""
        return {
            "name": self.ui.name_edit.text().strip(),
            "rate": self.ui.rate_spinbox.value(),
        }
    
    def set_data(self, data: dict) -> None:
        """Populate form from dictionary."""
        self.ui.name_edit.setText(data.get("name", ""))
        self.ui.rate_spinbox.setValue(data.get("rate", 0))
```

### Build Automation

**Makefile approach:**

```makefile
UI_DIR = ui/forms
GENERATED_DIR = ui/generated

.PHONY: compile-ui

compile-ui:
	@mkdir -p $(GENERATED_DIR)
	@for f in $(UI_DIR)/*.ui; do \
		base=$$(basename $$f .ui); \
		pyside6-uic $$f -o $(GENERATED_DIR)/ui_$${base}.py; \
	done
```

**Python script approach:**

```python
# scripts/compile_ui.py
import subprocess
from pathlib import Path

def compile_ui_files():
    """Compile all .ui files to Python."""
    ui_dir = Path("ui/forms")
    generated_dir = Path("ui/generated")
    generated_dir.mkdir(exist_ok=True)
    
    for ui_file in ui_dir.glob("*.ui"):
        output_file = generated_dir / f"ui_{ui_file.stem}.py"
        subprocess.run(
            ["pyside6-uic", str(ui_file), "-o", str(output_file)],
            check=True
        )
        print(f"Compiled: {ui_file.name} -> {output_file.name}")

if __name__ == "__main__":
    compile_ui_files()
```

**pyproject.toml integration:**

```toml
[tool.hatch.build.hooks.custom]
path = "scripts/compile_ui.py"
```

### Pros

- Better performance (no runtime parsing)
- IDE autocomplete and type hints
- Catch errors at compile time
- Can promote custom widgets
- Version control friendly (Python diffs)

### Cons

- Requires compilation step
- Must recompile after UI changes
- Generated code in repository (or build step)

### When to Use

- Production applications
- Team development (IDE support)
- When performance matters
- When using custom widget promotion

## Comparison Table

| Feature | QUiLoader | pyside6-uic |
|---------|-----------|-------------|
| Performance | Slower (runtime parsing) | Faster (pre-compiled) |
| IDE Support | No autocomplete | Full autocomplete |
| Type Hints | None | Generated |
| Error Detection | Runtime | Compile time |
| Build Step | Not needed | Required |
| Custom Widgets | Limited | Full support |
| Hot Reload | Possible | Requires recompile |
| File Size | Smaller (.ui only) | Larger (.ui + .py) |

## Recommendation

**For development:** Use pyside6-uic with auto-recompile on file changes.

**For production:** Always use pyside6-uic for performance and reliability.

**For prototyping:** QUiLoader is acceptable for quick experiments.

## Custom Widget Promotion

### In Qt Designer

1. Right-click widget → "Promote to..."
2. Set promoted class name (e.g., `CustomSpinBox`)
3. Set header file (e.g., `ui.components.custom_spinbox`)
4. Click "Add" then "Promote"

### Python Implementation

```python
# ui/components/custom_spinbox.py
from PySide6.QtWidgets import QSpinBox

class CustomSpinBox(QSpinBox):
    """Custom spinbox with validation."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimum(0)
        self.setMaximum(999999)
        self.setDecimals(2)
    
    def validate_input(self) -> bool:
        """Validate current value."""
        return self.value() > 0
```

### Generated Code

After promotion, pyside6-uic generates:

```python
from ui.components.custom_spinbox import CustomSpinBox

# In setupUi method:
self.rate_spinbox = CustomSpinBox(self.form_layout)
```

## Error Handling

### QUiLoader Errors

```python
loader = QUiLoader()
ui_file = QFile("form.ui")

if not ui_file.open(QFile.ReadOnly):
    raise FileNotFoundError(f"Cannot open UI: {ui_file.errorString()}")

widget = loader.load(ui_file, parent)
ui_file.close()

if widget is None:
    raise RuntimeError(f"UI load failed: {loader.errorString()}")
```

### pyside6-uic Errors

```python
try:
    from ui.generated.ui_form import Ui_Form
except ImportError as e:
    raise RuntimeError(
        f"Compiled UI not found. Run: pyside6-uic ui/form.ui -o ui/generated/ui_form.py"
    ) from e
```

## Migration Guide

### From QUiLoader to pyside6-uic

1. Compile your .ui file:
   ```bash
   pyside6-uic ui/form.ui -o ui/generated/ui_form.py
   ```

2. Update your class:
   ```python
   # Before (QUiLoader)
   self.ui = QUiLoader().load("ui/form.ui", self)
   
   # After (pyside6-uic)
   from ui.generated.ui_form import Ui_Form
   self.ui = Ui_Form()
   self.ui.setupUi(self)
   ```

3. Verify all widget accesses work (IDE will help catch typos)

4. Remove runtime UI loading code
