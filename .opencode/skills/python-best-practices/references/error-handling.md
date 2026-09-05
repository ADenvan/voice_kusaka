# Error Handling Best Practices

Comprehensive guide to exception handling in Python.

## Exception Hierarchy

Python's built-in exception hierarchy:

```
BaseException
 ├── SystemExit              # Raised by sys.exit()
 ├── KeyboardInterrupt       # User pressed Ctrl+C
 ├── GeneratorExit           # Generator's close() method
 └── Exception               # Base for all non-exit exceptions
      ├── ArithmeticError
      │    ├── ZeroDivisionError
      │    └── OverflowError
      ├── LookupError
      │    ├── IndexError
      │    └── KeyError
      ├── TypeError
      ├── ValueError
      │    └── UnicodeError
      ├── OSError
      │    ├── FileNotFoundError
      │    ├── PermissionError
      │    └── TimeoutError
      ├── RuntimeError
      ├── NameError
      │    └── UnboundLocalError
      ├── AttributeError
      ├── ImportError
      │    └── ModuleNotFoundError
      └── StopIteration
```

## Basic Try/Except

### Catching Specific Exceptions

```python
# Good - catch specific exceptions
def read_file(path: str) -> str:
    try:
        with open(path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        print(f"File not found: {path}")
        return ""
    except PermissionError:
        print(f"Permission denied: {path}")
        return ""

# Bad - catching everything
except:  # NEVER do this!
    pass

# Acceptable - catching Exception (but prefer specific)
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

### Exception Information

```python
def divide_numbers(a: float, b: float) -> float:
    try:
        return a / b
    except ZeroDivisionError as e:
        # 'e' contains the error message
        print(f"Cannot divide: {e}")
        raise ValueError(f"Division by zero: {a}/{b}") from e
```

## Multiple Except Blocks

Order matters - catch specific exceptions before general ones:

```python
import json

def parse_config(path: str) -> dict:
    try:
        with open(path, 'r') as f:
            content = f.read()
        return json.loads(content)
    except FileNotFoundError:
        logger.error(f"Config file missing: {path}")
        return {}
    except PermissionError:
        logger.error(f"Cannot read config: {path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {path}: {e}")
        return {}
    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception(f"Unexpected error reading {path}")
        raise
```

## Try/Except/Else/Finally

### Complete Structure

```python
def process_data(filepath: str) -> list:
    data = []
    
    try:
        # Code that might raise exception
        with open(filepath, 'r') as f:
            raw_data = f.read()
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        return []
    except PermissionError:
        logger.error(f"Permission denied: {filepath}")
        raise
    else:
        # Executes if NO exception occurred
        # Good for code that shouldn't trigger exception handling
        data = json.loads(raw_data)
        logger.info(f"Loaded {len(data)} records")
    finally:
        # ALWAYS executes (cleanup code)
        # Good for releasing resources
        logger.debug(f"Processing complete for {filepath}")
    
    return data
```

### Practical Example

```python
import tempfile
import os

def process_large_file(input_path: str) -> str:
    """Process file and return output path."""
    temp_path = None
    
    try:
        # Create temporary file
        temp_fd, temp_path = tempfile.mkstemp(suffix='.tmp')
        
        # Process data
        with open(input_path, 'r') as infile, \
             os.fdopen(temp_fd, 'w') as outfile:
            for line in infile:
                processed = line.upper()
                outfile.write(processed)
        
        return temp_path
        
    except FileNotFoundError:
        logger.error(f"Input file not found: {input_path}")
        if temp_path:
            os.unlink(temp_path)
        raise
    except Exception:
        # Clean up temp file on any error
        if temp_path:
            os.unlink(temp_path)
        raise
```

## Context Managers (with Statement)

Context managers ensure cleanup even with exceptions:

```python
# Good - automatic resource cleanup
with open('file.txt', 'r') as f:
    content = f.read()  # File closed automatically, even if exception

# Database connections
import sqlite3

with sqlite3.connect('database.db') as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    results = cursor.fetchall()
    conn.commit()  # Auto-committed or rolled back

# Multiple context managers
with open('input.txt', 'r') as infile, \
     open('output.txt', 'w') as outfile:
    for line in infile:
        outfile.write(line.upper())
```

### Custom Context Managers

```python
from contextlib import contextmanager
import logging
import time

@contextmanager
def timed_execution(operation_name: str):
    """Context manager to time operations."""
    start = time.time()
    logger.info(f"Starting: {operation_name}")
    
    try:
        yield  # Code inside 'with' block runs here
    except Exception:
        logger.error(f"{operation_name} failed after {time.time() - start:.2f}s")
        raise
    else:
        logger.info(f"{operation_name} completed in {time.time() - start:.2f}s")


# Usage
with timed_execution("Data Processing"):
    process_large_dataset()


@contextmanager
def database_transaction(connection):
    """Context manager for database transactions."""
    cursor = connection.cursor()
    try:
        yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


# Usage
conn = sqlite3.connect('mydb.db')
with database_transaction(conn) as cursor:
    cursor.execute("INSERT INTO users (name) VALUES (?)", ("Alice",))
    cursor.execute("INSERT INTO logs (action) VALUES (?)", ("create_user",))
```

## Exception Chaining

### raise...from (Explicit Chaining)

```python
def parse_port(config: dict) -> int:
    try:
        port = int(config['port'])
    except KeyError:
        raise ConfigurationError("Port not specified") from None
    except ValueError as e:
        raise ConfigurationError(f"Invalid port: {config['port']}") from e
    
    if not 1 <= port <= 65535:
        raise ConfigurationError(f"Port out of range: {port}")
    
    return port
```

### Preserving Tracebacks

```python
def process_user(user_id: int) -> dict:
    try:
        user = fetch_from_database(user_id)
        validate_user(user)
        return user
    except DatabaseError:
        # Re-raise preserving original traceback
        raise
    except ValidationError as e:
        # Convert to different exception type
        raise ProcessingError(f"User {user_id} invalid") from e
```

## Custom Exceptions

### Creating Custom Exception Classes

```python
class ApplicationError(Exception):
    """Base exception for this application."""
    pass


class ValidationError(ApplicationError):
    """Raised when data validation fails."""
    
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"Validation error in '{field}': {message}")


class NotFoundError(ApplicationError):
    """Raised when a resource is not found."""
    
    def __init__(self, resource_type: str, resource_id: str):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(f"{resource_type} '{resource_id}' not found")


class ConfigurationError(ApplicationError):
    """Raised when there's a configuration problem."""
    pass


class APIError(ApplicationError):
    """Raised when an API call fails."""
    
    def __init__(self, message: str, status_code: int = None, response_body: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
```

### Using Custom Exceptions

```python
def create_user(data: dict) -> User:
    """Create a new user."""
    # Validation
    if not data.get('email'):
        raise ValidationError('email', 'Email is required')
    
    if not data.get('name'):
        raise ValidationError('name', 'Name is required')
    
    # Check for existing user
    if user_exists(data['email']):
        raise ValidationError('email', 'Email already registered')
    
    # Database operation
    try:
        user = User.create(**data)
    except DatabaseError as e:
        logger.exception("Database error creating user")
        raise ApplicationError("Failed to create user") from e
    
    return user


def get_user(user_id: int) -> User:
    """Get user by ID."""
    user = User.query.get(user_id)
    if user is None:
        raise NotFoundError('User', str(user_id))
    return user
```

## Logging Exceptions

### Best Practices

```python
import logging
import traceback

logger = logging.getLogger(__name__)


def process_items(items: list) -> list:
    results = []
    
    for item in items:
        try:
            result = process_single(item)
            results.append(result)
        except Exception:
            # logger.exception includes stack trace
            logger.exception(f"Failed to process item: {item}")
            # Continue processing other items
            continue
    
    return results


def critical_operation():
    try:
        perform_critical_task()
    except Exception as e:
        # Log with stack trace then re-raise
        logger.critical(
            f"Critical operation failed: {e}",
            exc_info=True  # Include traceback
        )
        raise


def handle_api_error(response):
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        # Log structured error info
        logger.error(
            "API request failed",
            extra={
                'status_code': response.status_code,
                'url': response.url,
                'response_body': response.text[:1000]
            }
        )
        raise
```

### Log Levels for Exceptions

```python
def fetch_data(url: str) -> dict:
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        # Expected error, can retry
        logger.warning(f"Request timeout: {url}")
        raise RetryableError("Timeout")
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            # Expected error, resource not found
            logger.info(f"Resource not found: {url}")
            return {}
        elif e.response.status_code >= 500:
            # Server error, might be temporary
            logger.warning(f"Server error {e.response.status_code}: {url}")
            raise RetryableError("Server error")
        else:
            # Client error, don't retry
            logger.error(f"Client error {e.response.status_code}: {url}")
            raise
    except requests.RequestException:
        # Network error, might be temporary
        logger.warning(f"Network error for {url}", exc_info=True)
        raise RetryableError("Network error")
```

## EAFP vs LBYL

### EAFP (Easier to Ask Forgiveness than Permission)

```python
# Pythonic - EAFP
def get_config_value(config: dict, key: str, default=None):
    try:
        return config[key]
    except KeyError:
        return default

# Alternative using dict.get()
def get_config_value(config: dict, key: str, default=None):
    return config.get(key, default)
```

### LBYL (Look Before You Leap)

```python
# Non-Pythonic - LBYL
def get_config_value(config: dict, key: str, default=None):
    if key in config:
        return config[key]
    return default
```

### When to Use Each

```python
# EAFP - preferred in Python
# Better when race conditions possible

def read_file_atomic(path: str) -> str:
    """Read file content."""
    try:
        with open(path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return ""


# LBYL - acceptable for expensive operations

def process_if_valid(data: dict) -> None:
    """Process data only if it passes all validations."""
    # Check everything first (might be expensive)
    errors = validate_data(data)
    if errors:
        raise ValidationError(errors)
    
    # Then process (also expensive, don't want to rollback)
    process_data(data)
```

## Retry Patterns

```python
import time
import random
from functools import wraps

def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Retry decorator with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 1
            current_delay = delay
            
            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except RetryableError as e:
                    if attempt == max_attempts:
                        logger.error(f"Max retries ({max_attempts}) exceeded")
                        raise
                    
                    logger.warning(
                        f"Attempt {attempt} failed: {e}. "
                        f"Retrying in {current_delay}s..."
                    )
                    
                    # Add jitter to prevent thundering herd
                    jitter = random.uniform(0, current_delay * 0.1)
                    time.sleep(current_delay + jitter)
                    
                    current_delay *= backoff
                    attempt += 1
            
            return None  # Should never reach here
        
        return wrapper
    return decorator


# Usage
@retry(max_attempts=3, delay=1.0, backoff=2.0)
def fetch_data_from_api(url: str) -> dict:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()
```

## Common Pitfalls

### Don't Catch BaseException

```python
# BAD - catches KeyboardInterrupt, SystemExit
except BaseException:
    pass

# BAD - catches KeyboardInterrupt
except Exception:
    pass

# GOOD - catch specific exceptions
except (ValueError, TypeError):
    pass
```

### Don't Swallow Exceptions

```python
# BAD - silently ignores all errors
try:
    do_something()
except Exception:
    pass

# GOOD - at least log the error
try:
    do_something()
except Exception:
    logger.exception("Operation failed")
    raise  # Re-raise or handle meaningfully
```

### Don't Use Exceptions for Flow Control

```python
# BAD - using exceptions for normal flow
def find_user(users: list, user_id: int):
    try:
        return next(u for u in users if u.id == user_id)
    except StopIteration:
        return None

# GOOD - use built-in methods
def find_user(users: list, user_id: int):
    for user in users:
        if user.id == user_id:
            return user
    return None

# BETTER - if using generator
def find_user(users: list, user_id: int):
    return next(
        (u for u in users if u.id == user_id),
        None
    )
```

## References

- Python Docs: https://docs.python.org/3/tutorial/errors.html
- Exception Hierarchy: https://docs.python.org/3/library/exceptions.html
- Context Managers: https://docs.python.org/3/reference/datamodel.html#context-managers
