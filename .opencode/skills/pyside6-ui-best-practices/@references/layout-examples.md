# Layout Examples

Complex layout combinations and best practices for PySide6.

## Basic Layouts

### QVBoxLayout - Vertical Stacking

```python
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel

class VerticalExample(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Title"))
        layout.addWidget(QPushButton("Button 1"))
        layout.addWidget(QPushButton("Button 2"))
        layout.addWidget(QPushButton("Button 3"))
        
        # Add stretch to push content to top
        layout.addStretch()
```

### QHBoxLayout - Horizontal Stacking

```python
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton

class HorizontalExample(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        
        layout.addWidget(QPushButton("Left"))
        layout.addStretch()  # Push right button to end
        layout.addWidget(QPushButton("Right"))
```

### QGridLayout - Grid Arrangement

```python
from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton

class GridExample(QWidget):
    def __init__(self):
        super().__init__()
        layout = QGridLayout(self)
        
        # row, col, rowSpan, colSpan
        layout.addWidget(QPushButton("1,1"), 0, 0)
        layout.addWidget(QPushButton("1,2"), 0, 1)
        layout.addWidget(QPushButton("2,1"), 1, 0)
        layout.addWidget(QPushButton("2,2"), 1, 1)
        
        # Spanning multiple columns
        layout.addWidget(QPushButton("Full Width"), 2, 0, 1, 2)
        
        # Set column stretch
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 2)  # Column 1 is twice as wide
```

### QFormLayout - Label-Field Pairs

```python
from PySide6.QtWidgets import QWidget, QFormLayout, QLineEdit, QSpinBox

class FormExample(QWidget):
    def __init__(self):
        super().__init__()
        layout = QFormLayout(self)
        
        layout.addRow("Name:", QLineEdit())
        layout.addRow("Email:", QLineEdit())
        layout.addRow("Age:", QSpinBox())
        layout.addRow("Bio:", QLineEdit())
        
        # Set label alignment
        layout.setLabelAlignment(Qt.AlignRight)
        
        # Set field growth policy
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
```

## Nested Layouts

### Form with Button Bar

```python
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QHBoxLayout
from PySide6.QtWidgets import QLineEdit, QSpinBox, QPushButton

class EmployeeForm(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)
        
        # Form section
        form_layout = QFormLayout()
        form_layout.addRow("Name:", QLineEdit())
        form_layout.addRow("Rate:", QSpinBox())
        form_layout.addRow("Department:", QLineEdit())
        main_layout.addLayout(form_layout)
        
        # Separator
        from PySide6.QtWidgets import QFrame
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)
        
        # Button section
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(QPushButton("Save"))
        button_layout.addWidget(QPushButton("Cancel"))
        main_layout.addLayout(button_layout)
```

### Complex Dashboard Layout

```python
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSplitter
from PySide6.QtWidgets import QTableWidget, QTextEdit, QLabel

class Dashboard(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Dashboard"))
        header_layout.addStretch()
        header_layout.addWidget(QPushButton("Refresh"))
        main_layout.addLayout(header_layout)
        
        # Main content with splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - table
        table = QTableWidget(10, 4)
        splitter.addWidget(table)
        
        # Right panel - details
        details = QTextEdit()
        details.setReadOnly(True)
        splitter.addWidget(details)
        
        # Set initial sizes
        splitter.setSizes([600, 400])
        main_layout.addWidget(splitter)
        
        # Status bar
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("Ready"))
        main_layout.addLayout(status_layout)
```

## Spacing and Margins

### Control Layout Spacing

```python
layout = QVBoxLayout(self)

# Set margins (left, top, right, bottom)
layout.setContentsMargins(10, 10, 10, 10)

# Set spacing between widgets
layout.setSpacing(15)

# Individual widget spacing
layout.addWidget(widget1)
layout.addSpacing(20)  # Fixed space
layout.addWidget(widget2)
layout.addStretch()    # Flexible space
```

### Widget Alignment in Layouts

```python
layout = QHBoxLayout()

# Add widget with alignment
layout.addWidget(widget, alignment=Qt.AlignTop)
layout.addWidget(widget, alignment=Qt.AlignCenter)
layout.addWidget(widget, alignment=Qt.AlignBottom)

# Set size policy
widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
```

## Common Patterns

### Centered Dialog Content

```python
class CenteredDialog(QDialog):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        # Top stretch (pushes content to center)
        layout.addStretch()
        
        # Centered content
        content_layout = QVBoxLayout()
        content_layout.addWidget(QLabel("Important Message"))
        content_layout.addWidget(QPushButton("OK"))
        layout.addLayout(content_layout)
        
        # Bottom stretch
        layout.addStretch()
```

### Scrollable Form

```python
from PySide6.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QFormLayout

class ScrollableForm(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        # Container widget for scroll content
        scroll_content = QWidget()
        form_layout = QFormLayout(scroll_content)
        
        # Add many fields
        for i in range(20):
            form_layout.addRow(f"Field {i}:", QLineEdit())
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
```

### Tabbed Interface

```python
from PySide6.QtWidgets import QTabWidget, QWidget, QVBoxLayout

class TabbedWindow(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        tabs = QTabWidget()
        
        # Tab 1
        tab1 = QWidget()
        tab1_layout = QVBoxLayout(tab1)
        tab1_layout.addWidget(QLabel("Employees"))
        tabs.addTab(tab1, "Employees")
        
        # Tab 2
        tab2 = QWidget()
        tab2_layout = QVBoxLayout(tab2)
        tab2_layout.addWidget(QLabel("Reports"))
        tabs.addTab(tab2, "Reports")
        
        layout.addWidget(tabs)
```

## Size Policies

### Understanding SizePolicy

```python
from PySide6.QtWidgets import QSizePolicy

# Horizontal | Vertical
QSizePolicy.Expanding    # Widget wants to grow
QSizePolicy.Minimum      # Widget can shrink to minimum
QSizePolicy.Fixed        # Widget cannot resize
QSizePolicy.Preferred    # Widget prefers sizeHint but can shrink
QSizePolicy.Maximum      # Widget can shrink to any size

# Example
label = QLabel("Fixed height, expanding width")
label.setSizePolicy(
    QSizePolicy.Expanding,  # Horizontal
    QSizePolicy.Fixed       # Vertical
)

button = QPushButton("Fixed size")
button.setSizePolicy(
    QSizePolicy.Fixed,
    QSizePolicy.Fixed
)
```

### Stretch Factors

```python
layout = QHBoxLayout()

# Widgets with different stretch factors
layout.addWidget(small_widget, stretch=1)
layout.addWidget(large_widget, stretch=3)
# large_widget gets 3x the space of small_widget

# Equal distribution
layout.addWidget(widget1, stretch=1)
layout.addWidget(widget2, stretch=1)
```

## Best Practices

1. **Always use layouts** - Never use fixed positions
2. **Test resizing** - Ensure UI works at different window sizes
3. **Use stretch factors** - For proportional space distribution
4. **Set minimum sizes** - Prevent widgets from becoming too small
5. **Use QSplitter** - For user-resizable panels
6. **Group related widgets** - Use QGroupBox for logical sections
7. **Add margins** - Don't let content touch window edges
8. **Use spacers** - For flexible positioning

## Anti-Patterns

```python
# BAD - Fixed positions
widget.move(100, 200)
widget.resize(300, 100)

# BAD - No layout
class BadWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.button = QPushButton("Click")
        # No layout set - button won't appear properly

# BAD - Fixed sizes everywhere
widget.setFixedSize(400, 300)  # Only for dialogs

# GOOD - Flexible layout
class GoodWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QPushButton("Click"))
```
