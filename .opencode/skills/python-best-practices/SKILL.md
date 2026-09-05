---
name: python-best-practices
description: |
    Write clean, maintainable, and professional Python code following PEP 8, modern conventions, and industry best practices. Covers code structure, error handling, type hints, logging, and project organization.
    Use when writing or refactoring Python code, reviewing code quality, or setting up new Python projects.
origin: community
metadata:
  author: opencode
  version: "1.0"
---

# Python Best Practices

Write professional, maintainable Python code following industry standards and modern conventions.

## When to use this skill

- Writing new Python code or scripts
- Refactoring existing Python code
- Setting up a new Python project
- Code review and quality improvements
- Adding error handling and logging
- Implementing type hints

## Quick Start

### Professional Python File Template

```python
"""Module description - one line summary.

More detailed description of what this module does and how to use it.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Configure logging
logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30


def process_data(input_path: Path, output_path: Optional[Path] = None) -> bool:
    """Process data from input file.

    Args:
        input_path: Path to input file
        output_path: Optional path for output (default: input_path with .out suffix)

    Returns:
        True if processing succeeded, False otherwise

    Raises:
        FileNotFoundError: If input file doesn't exist
        PermissionError: If lacking permissions to read/write files
    """
    logger.info(f"Processing {input_path}")

    try:
        # Read input
        with open(input_path, 'r', encoding='utf-8') as f:
            data = f.read()

        # Process data
        result = data.upper()  # Example transformation

        # Write output
        if output_path is None:
            output_path = input_path.with_suffix('.out')

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result)

        logger.info(f"Output written to {output_path}")
        return True

    except FileNotFoundError:
        logger.error(f"Input file not found: {input_path}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error processing {input_path}")
        return False


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Example usage
    if len(sys.argv) < 2:
        print("Usage: python script.py <input_file>")
        return 1

    input_file = Path(sys.argv[1])
    success = process_data(input_file)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
```

## Core Principles

### 1. PEP 8 Compliance

Always follow PEP 8 style guide:

**Naming Conventions:**
- `snake_case` for functions, variables, modules
- `PascalCase` for classes
- `UPPER_CASE` for constants
- `_leading_underscore` for internal use

```python
# Good
MAX_CONNECTIONS = 100  # Constants
user_name = "John"     # Variables
def fetch_data():      # Functions
    pass
class DataProcessor:   # Classes
    pass

# Bad
maxConnections = 100   # Wrong case
UserName = "John"      # Wrong case
def FetchData():       # Wrong case
    pass
class data_processor:  # Wrong case
    pass
```

**Indentation & Spacing:**
- Use 4 spaces per indentation level (never tabs)
- Maximum line length: 88 characters (Ruff formatter) or 79 (PEP 8)
- Two blank lines between top-level definitions
- One blank line between method definitions

```python
# Good
class DataProcessor:
    """Process data."""

    def __init__(self):
        self.data = []

    def process(self):
        """Process the data."""
        if self.data:
            return sum(self.data)
        return 0


def helper_function():
    """Helper function."""
    pass
```

### 2. Import Organization

Organize imports in three groups with blank lines between:

```python
# 1. Standard library imports
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict

# 2. Third-party imports
import requests
import pandas as pd
from pydantic import BaseModel

# 3. Local application imports
from mypackage import utils
from mypackage.models import User
```

Use absolute imports over relative imports:

```python
# Good
from mypackage.module import MyClass

# Avoid
from .module import MyClass
from ..utils import helper
```

### 3. Type Hints

Always use type hints for function signatures:

```python
from typing import Optional, List, Dict, Union

def calculate_total(
    items: List[Dict[str, Union[int, float]]],
    tax_rate: float = 0.0
) -> float:
    """Calculate total with optional tax.

    Args:
        items: List of items with 'price' key
        tax_rate: Tax rate as decimal (0.0 to 1.0)

    Returns:
        Total amount including tax
    """
    subtotal = sum(item.get('price', 0) for item in items)
    return subtotal * (1 + tax_rate)


# Optional parameters
def greet(name: str, greeting: Optional[str] = None) -> str:
    """Greet a person."""
    if greeting is None:
        greeting = "Hello"
    return f"{greeting}, {name}!"
```

See [Type Hints Guide](references/type-hints.md) for advanced usage.

### 4. Error Handling

Catch specific exceptions first, use context managers for resources:

```python
# Good - specific exceptions, resource cleanup
def read_config(path: Path) -> dict:
    """Read configuration from file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return parse_config(content)
    except FileNotFoundError:
        logger.error(f"Config file not found: {path}")
        return {}
    except PermissionError:
        logger.error(f"Permission denied: {path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {path}: {e}")
        return {}

# Bad - catching everything, no cleanup
def read_config_bad(path):
    f = open(path, 'r')  # Resource leak!
    try:
        return json.load(f)
    except:  # Bare except - catches KeyboardInterrupt!
        return {}
```

See [Error Handling Guide](references/error-handling.md) for complete patterns.

### 5. Documentation

Use Google-style docstrings:

```python
def process_order(
    order_id: str,
    items: List[Dict[str, Any]],
    customer_email: str,
    priority: str = "normal"
) -> OrderResult:
    """Process a customer order.

    Args:
        order_id: Unique order identifier
        items: List of order items with 'sku', 'quantity', 'price' keys
        customer_email: Customer email for notifications
        priority: Order priority ('low', 'normal', 'high', 'urgent')

    Returns:
        OrderResult with order details and status

    Raises:
        ValueError: If order_id is empty or items list is empty
        InvalidEmailError: If customer_email format is invalid
        OutOfStockError: If any item is out of stock

    Example:
        >>> result = process_order(
        ...     "ORD-123",
        ...     [{"sku": "ABC", "quantity": 2, "price": 10.0}],
        ...     "customer@example.com"
        ... )
        >>> result.status
        'confirmed'
    """
    ...
```

### 6. Logging

Use logging module instead of print statements:

```python
import logging

# Get logger for this module
logger = logging.getLogger(__name__)


def process_data(data: list) -> list:
    """Process data items."""
    logger.info(f"Processing {len(data)} items")

    results = []
    for item in data:
        try:
            result = transform(item)
            results.append(result)
            logger.debug(f"Transformed {item} -> {result}")
        except Exception as e:
            logger.warning(f"Failed to transform {item}: {e}")
            continue

    logger.info(f"Completed: {len(results)}/{len(data)} succeeded")
    return results
```

**Log Levels:**
- `DEBUG`: Detailed information for debugging
- `INFO`: Confirmation that things are working
- `WARNING`: Something unexpected happened, but working
- `ERROR`: Something failed, but not fatal
- `CRITICAL`: Fatal error, program may not continue

## Common Patterns

### Pattern 1: Main Guard

Always use `if __name__ == "__main__":` guard:

```python
def main() -> int:
    """Main entry point."""
    try:
        result = run_application()
        return 0 if result else 1
    except Exception as e:
        logger.exception("Application failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

### Pattern 2: Context Managers

Use `with` statement for resource management:

```python
# File operations
with open('data.txt', 'r') as f:
    content = f.read()
# File automatically closed

# Database connections
with get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
# Connection automatically closed/returned to pool

# Locks
with threading.Lock():
    shared_resource.modify()
# Lock automatically released
```

### Pattern 3: List Comprehensions vs Generators

Use appropriate construct for the use case:

```python
# List comprehension - when you need the whole list
squares = [x**2 for x in range(1000)]

# Generator expression - memory efficient for large data
squares_gen = (x**2 for x in range(1000000))

# Dictionary comprehension
name_lengths = {name: len(name) for name in names}

# Set comprehension
unique_chars = {c for c in long_string}
```

### Pattern 4: Pathlib over os.path

Use `pathlib` for path operations:

```python
from pathlib import Path

# Good
config_path = Path.home() / '.config' / 'myapp' / 'config.json'
if config_path.exists():
    content = config_path.read_text()

# Avoid
import os
config_path = os.path.join(os.path.expanduser('~'), '.config', 'myapp', 'config.json')
if os.path.exists(config_path):
    with open(config_path) as f:
        content = f.read()
```

### Pattern 5: f-strings for Formatting

Use f-strings for string formatting:

```python
name = "Alice"
age = 30

# Good
message = f"Hello, {name}! You are {age} years old."

# Acceptable for templates
template = "Hello, {name}!"
message = template.format(name=name)

# Avoid
message = "Hello, %s! You are %d years old." % (name, age)
```

## Best Practices

### 1. Avoid Mutable Default Arguments

```python
# Bad - mutable default
def append_item(item, items=[]):
    items.append(item)
    return items

# Good - None default
def append_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
```

### 2. Use `is` for None Checks

```python
# Good
if x is None:
    pass

if x is not None:
    pass

# Avoid
if x == None:
    pass
```

### 3. Use Truthy/Falsy Values

```python
# Good
if items:  # Checks for non-empty
    process(items)

if not name:  # Checks for empty/None
    raise ValueError("Name required")

# Avoid
if len(items) > 0:
    process(items)

if name == "":
    raise ValueError("Name required")
```

### 4. EAFP vs LBYL

Prefer "Easier to Ask Forgiveness than Permission":

```python
# EAFP - Pythonic
try:
    value = my_dict[key]
except KeyError:
    value = default

# LBYL - Less Pythonic
if key in my_dict:
    value = my_dict[key]
else:
    value = default

# Or use dict.get()
value = my_dict.get(key, default)
```

### 5. Single Responsibility

Keep functions and classes focused:

```python
# Bad - does too much
def process_user_data(user_data):
    # Validate
    if not user_data.get('email'):
        raise ValueError()
    # Transform
    user_data['email'] = user_data['email'].lower()
    # Save
    db.insert(user_data)
    # Notify
    send_email(user_data['email'])

# Good - separate concerns
def validate_user(user_data: dict) -> None:
    """Validate user data."""
    if not user_data.get('email'):
        raise ValueError("Email required")

def normalize_user(user_data: dict) -> dict:
    """Normalize user data."""
    return {**user_data, 'email': user_data['email'].lower()}

def save_user(user_data: dict) -> None:
    """Save user to database."""
    db.insert(user_data)
```

## References

- [PEP 8 Style Guide](references/pep8-style-guide.md) - Complete PEP 8 reference
- [Error Handling](references/error-handling.md) - Exception handling patterns
- [Type Hints](references/type-hints.md) - Type annotation guide
- [Project Structure](references/project-structure.md) - Project organization
- [Project Template](scripts/project_template.py) - Production-ready template

## Official Resources

- PEP 8: https://peps.python.org/pep-0008/
- Google Python Style Guide: https://google.github.io/styleguide/pyguide.html
- Python Documentation: https://docs.python.org/3/
