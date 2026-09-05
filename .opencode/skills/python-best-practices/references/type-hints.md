# Type Hints Guide

Complete guide to Python type hints (PEP 484 and later).

## Basic Type Annotations

### Function Signatures

```python
# Basic types
def greet(name: str) -> str:
    """Greet a person."""
    return f"Hello, {name}"

def add(x: int, y: int) -> int:
    """Add two integers."""
    return x + y

def divide(a: float, b: float) -> float:
    """Divide two numbers."""
    return a / b

# Multiple parameters
def create_user(
    name: str,
    email: str,
    age: int,
    is_active: bool = True
) -> dict:
    """Create a user dictionary."""
    return {
        "name": name,
        "email": email,
        "age": age,
        "is_active": is_active
    }
```

### Variable Annotations

```python
# Variable types
name: str = "Alice"
age: int = 30
pi: float = 3.14159
is_valid: bool = True

# Without initialization
count: int
message: str

# Class attributes
class User:
    name: str
    age: int
    
    def __init__(self, name: str, age: int) -> None:
        self.name = name
        self.age = age
```

## Collection Types

### Lists, Sets, Tuples

```python
from typing import List, Set, Tuple

# List - homogeneous elements
def process_items(items: List[str]) -> List[str]:
    """Process a list of strings."""
    return [item.upper() for item in items]

numbers: List[int] = [1, 2, 3, 4, 5]
names: List[str] = ["Alice", "Bob", "Charlie"]

# Set - unique elements
def unique_tags(tags: Set[str]) -> Set[str]:
    """Process unique tags."""
    return {tag.lower() for tag in tags}

allowed: Set[str] = {"read", "write", "execute"}

# Tuple - fixed size, fixed types
def get_coordinates() -> Tuple[float, float]:
    """Get x, y coordinates."""
    return (10.5, 20.3)

# Tuple with named elements
from typing import NamedTuple

class Point(NamedTuple):
    x: float
    y: float
    
def move_point(p: Point, dx: float, dy: float) -> Point:
    return Point(p.x + dx, p.y + dy)
```

### Dictionaries

```python
from typing import Dict, Mapping, MutableMapping

# Simple dictionary
def count_words(words: List[str]) -> Dict[str, int]:
    """Count word frequencies."""
    result: Dict[str, int] = {}
    for word in words:
        result[word] = result.get(word, 0) + 1
    return result

# Nested dictionaries
config: Dict[str, Dict[str, str]] = {
    "database": {
        "host": "localhost",
        "port": "5432"
    }
}

# Read-only vs mutable
from typing import Mapping, MutableMapping

def read_config(config: Mapping[str, str]) -> None:
    """Read-only access to config."""
    print(config.get("key"))

def update_config(config: MutableMapping[str, str]) -> None:
    """Can modify config."""
    config["new_key"] = "value"
```

## Optional and Union Types

### Optional

```python
from typing import Optional

# Optional parameter
def greet(name: Optional[str] = None) -> str:
    """Greet a person (or default)."""
    if name is None:
        return "Hello, stranger!"
    return f"Hello, {name}!"

# Optional return
def find_user(user_id: int) -> Optional[dict]:
    """Find user or return None."""
    # ... search logic
    return None  # or user dict

# Equivalent to Optional
def find_user(user_id: int) -> dict | None:  # Python 3.10+
    pass
```

### Union Types

```python
from typing import Union

# Multiple possible types
def parse_value(value: Union[str, int, float]) -> float:
    """Parse numeric value."""
    if isinstance(value, str):
        return float(value)
    return float(value)

# Modern syntax (Python 3.10+)
def parse_value(value: str | int | float) -> float:
    pass

# Return different types
def get_data(id: int) -> Union[dict, list]:
    """Get data that could be dict or list."""
    pass
```

## Type Aliases

```python
from typing import Dict, List, Tuple, Union

# Simple alias
Vector = List[float]

def scale_vector(v: Vector, factor: float) -> Vector:
    """Scale a vector."""
    return [x * factor for x in v]

# Complex alias
JsonValue = Union[
    None, bool, int, float, str,
    List['JsonValue'],
    Dict[str, 'JsonValue']
]

def parse_json(data: str) -> JsonValue:
    import json
    return json.loads(data)

# Type alias for function signatures
HandlerFunction = Callable[[Request], Response]

# Database row type
Row = Tuple[int, str, str, Optional[datetime]]
```

## Classes and Objects

### Class Methods

```python
from typing import Self  # Python 3.11+

class Vector:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
    
    def __add__(self, other: 'Vector') -> 'Vector':
        """Add two vectors."""
        return Vector(self.x + other.x, self.y + other.y)
    
    def scale(self, factor: float) -> 'Vector':
        """Scale the vector."""
        return Vector(self.x * factor, self.y * factor)
    
    @classmethod
    def zero(cls) -> 'Vector':
        """Create zero vector."""
        return cls(0, 0)
    
    @classmethod
    def from_tuple(cls, coords: Tuple[float, float]) -> 'Vector':
        """Create from tuple."""
        return cls(coords[0], coords[1])


# With Self (Python 3.11+)
class Builder:
    def __init__(self) -> None:
        self._parts: List[str] = []
    
    def add(self, part: str) -> Self:
        self._parts.append(part)
        return self
    
    def build(self) -> str:
        return ''.join(self._parts)

# Usage: builder.add("a").add("b").build()
```

### Abstract Base Classes

```python
from abc import ABC, abstractmethod
from typing import Sequence

class Animal(ABC):
    @abstractmethod
    def speak(self) -> str:
        pass
    
    @abstractmethod
    def move(self) -> None:
        pass

class Dog(Animal):
    def speak(self) -> str:
        return "Woof!"
    
    def move(self) -> None:
        print("Running on 4 legs")

class Bird(Animal):
    def speak(self) -> str:
        return "Tweet!"
    
    def move(self) -> None:
        print("Flying")

# Accept any Animal
def make_speak(animal: Animal) -> str:
    return animal.speak()

# Accept sequence of animals
def zoo_sounds(animals: Sequence[Animal]) -> List[str]:
    return [animal.speak() for animal in animals]
```

## Generic Types

### Generic Functions

```python
from typing import TypeVar, Generic, List

T = TypeVar('T')

def first(items: List[T]) -> T | None:
    """Get first item or None."""
    return items[0] if items else None

# Works with any type
numbers: List[int] = [1, 2, 3]
n: int | None = first(numbers)

names: List[str] = ["Alice", "Bob"]
s: str | None = first(names)

# Bounded TypeVar
from typing import TypeVar

Number = TypeVar('Number', int, float)

def add(a: Number, b: Number) -> Number:
    """Add two numbers."""
    return a + b

# Only int or float allowed
add(1, 2)        # OK
add(1.5, 2.5)    # OK
add("a", "b")    # Type error!
```

### Generic Classes

```python
from typing import TypeVar, Generic, Optional

T = TypeVar('T')

class Stack(Generic[T]):
    """Generic stack implementation."""
    
    def __init__(self) -> None:
        self._items: List[T] = []
    
    def push(self, item: T) -> None:
        self._items.append(item)
    
    def pop(self) -> Optional[T]:
        if not self._items:
            return None
        return self._items.pop()
    
    def peek(self) -> Optional[T]:
        if not self._items:
            return None
        return self._items[-1]
    
    def is_empty(self) -> bool:
        return len(self._items) == 0

# Usage
int_stack: Stack[int] = Stack()
int_stack.push(1)
int_stack.push(2)
n: int | None = int_stack.pop()

str_stack: Stack[str] = Stack()
str_stack.push("hello")
s: str | None = str_stack.pop()
```

## Callable Types

```python
from typing import Callable

# Simple callback
def execute_callback(callback: Callable[[], None]) -> None:
    """Execute a callback function."""
    callback()

# Callback with arguments and return value
def process_data(
    data: List[int],
    transform: Callable[[int], str]
) -> List[str]:
    """Process data with custom transform."""
    return [transform(x) for x in data]

# Usage
results = process_data([1, 2, 3], lambda x: f"value: {x}")

# Multiple arguments
def binary_operation(
    a: int,
    b: int,
    op: Callable[[int, int], int]
) -> int:
    return op(a, b)

result = binary_operation(5, 3, lambda x, y: x + y)

# Optional callable
from typing import Optional

def process_with_optional_callback(
    data: str,
    callback: Optional[Callable[[str], None]] = None
) -> None:
    if callback:
        callback(data)
```

## Decorators and Type Hints

```python
from typing import TypeVar, Callable, Any
from functools import wraps

F = TypeVar('F', bound=Callable[..., Any])

def my_decorator(func: F) -> F:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        print("Before call")
        result = func(*args, **kwargs)
        print("After call")
        return result
    return wrapper  # type: ignore[return-value]


# Decorator with parameters
from typing import TypeVar

F = TypeVar('F', bound=Callable[..., Any])

def retry(max_attempts: int) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if attempt == max_attempts - 1:
                        raise
        return wrapper  # type: ignore[return-value]
    return decorator


# Modern approach with ParamSpec (Python 3.10+)
from typing import ParamSpec, TypeVar

P = ParamSpec('P')
T = TypeVar('T')

def timing_decorator(
    func: Callable[P, T]
) -> Callable[P, T]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        import time
        start = time.time()
        result = func(*args, **kwargs)
        print(f"Took {time.time() - start:.2f}s")
        return result
    return wrapper

@timing_decorator
def slow_function(n: int) -> int:
    import time
    time.sleep(n)
    return n * 2
```

## Protocol (Structural Subtyping)

```python
from typing import Protocol, runtime_checkable

# Define protocol (interface)
class Drawable(Protocol):
    def draw(self) -> None:
        ...

# Classes don't need to inherit from Drawable
class Circle:
    def draw(self) -> None:
        print("Drawing circle")

class Square:
    def draw(self) -> None:
        print("Drawing square")

class Text:
    pass  # No draw method

# Function accepts any "drawable" object
def render_all(items: List[Drawable]) -> None:
    for item in items:
        item.draw()

# Works with any class that has draw method
render_all([Circle(), Square()])  # OK
# render_all([Text()])  # Type error!


# Runtime checkable protocol
@runtime_checkable
class Sized(Protocol):
    def __len__(self) -> int:
        ...

def print_size(obj: Sized) -> None:
    print(f"Size: {len(obj)}")

# Can use isinstance at runtime
print(isinstance([1, 2, 3], Sized))  # True
```

## Type Checking at Runtime

```python
from typing import get_type_hints, get_origin, get_args

class User:
    def __init__(self, name: str, age: int) -> None:
        self.name = name
        self.age = age

# Get type hints
hints = get_type_hints(User.__init__)
print(hints)
# {'name': <class 'str'>, 'age': <class 'int'>, 'return': <class 'NoneType'>}

# Check if Optional
from typing import Optional, Union

def is_optional_type(t: type) -> bool:
    """Check if type is Optional[X]."""
    origin = get_origin(t)
    if origin is Union:
        args = get_args(t)
        return type(None) in args
    return False

# Usage
print(is_optional_type(Optional[str]))  # True
print(is_optional_type(str | None))     # True (Python 3.10+)
```

## Configuration for Type Checking

### mypy Configuration

```ini
# mypy.ini
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_decorators = False
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_unreachable = True
strict_equality = True

# Per-module settings
[mypy.plugins.sqlalchemy.*]
follow_imports = skip

[mypy-tests.*]
disallow_untyped_defs = False
```

### pyright Configuration

```json
// pyrightconfig.json
{
    "include": ["src"],
    "exclude": ["**/__pycache__"],
    "ignore": ["src/old_code"],
    "pythonVersion": "3.11",
    "pythonPlatform": "Linux",
    "strict": ["src"],
    "typeCheckingMode": "strict",
    "reportMissingImports": true,
    "reportMissingTypeStubs": false
}
```

## Common Type Checking Commands

```bash
# Install type checker
pip install mypy pyright

# Check single file
mypy myfile.py

# Check package
mypy mypackage/

# Check with specific config
mypy --config-file mypy.ini mypackage/

# Pyright check
pyright myfile.py
pyright --project myproject/

# Ignore specific line
value = some_function()  # type: ignore

# Ignore specific error
value = some_function()  # type: ignore[assignment]
```

## Type Hints in Practice

### Complete Example

```python
from typing import Optional, List, Dict, Protocol
from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    id: int
    name: str
    email: str
    created_at: datetime
    is_active: bool = True


class UserRepository(Protocol):
    """Protocol for user storage."""
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        ...
    
    def get_all(self) -> List[User]:
        ...
    
    def save(self, user: User) -> None:
        ...


class InMemoryUserRepository:
    """In-memory implementation."""
    
    def __init__(self) -> None:
        self._users: Dict[int, User] = {}
        self._next_id: int = 1
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        return self._users.get(user_id)
    
    def get_all(self) -> List[User]:
        return list(self._users.values())
    
    def save(self, user: User) -> None:
        if user.id == 0:
            user.id = self._next_id
            self._next_id += 1
        self._users[user.id] = user


class UserService:
    """Business logic for users."""
    
    def __init__(self, repository: UserRepository) -> None:
        self._repo = repository
    
    def get_user(self, user_id: int) -> Optional[User]:
        return self._repo.get_by_id(user_id)
    
    def create_user(self, name: str, email: str) -> User:
        user = User(
            id=0,
            name=name,
            email=email,
            created_at=datetime.now()
        )
        self._repo.save(user)
        return user
    
    def get_active_users(self) -> List[User]:
        return [u for u in self._repo.get_all() if u.is_active]


# Usage
repo: UserRepository = InMemoryUserRepository()
service = UserService(repo)

new_user = service.create_user("Alice", "alice@example.com")
print(f"Created user: {new_user.id}")
```

## References

- PEP 484: https://peps.python.org/pep-0484/
- PEP 526: https://peps.python.org/pep-0526/
- mypy: https://mypy.readthedocs.io/
- Pyright: https://github.com/microsoft/pyright
