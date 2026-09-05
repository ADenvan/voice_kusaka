# PEP 8 Style Guide

Complete reference for Python's official style guide (PEP 8).

## Indentation

Use **4 spaces** per indentation level. Never use tabs.

```python
# Good
class MyClass:
    def my_method(self):
        if condition:
            do_something()

# Bad - inconsistent indentation
class MyClass:
  def my_method(self):
      if condition:
        do_something()
```

### Continuation Lines

Align wrapped elements vertically or use hanging indent:

```python
# Aligned with opening delimiter
def long_function_name(
        var_one, var_two, var_three,
        var_four, var_five):
    print(var_one)

# Hanging indent (4 spaces)
def long_function_name(
    var_one, var_two, var_three,
    var_four, var_five
):
    print(var_one)

# For function calls
result = some_function(
    'a', 'b', 'c',
    'd', 'e', 'f'
)
```

## Maximum Line Length

Limit lines to **79 characters** (PEP 8 strict) or **88 characters** (Ruff formatter).

```python
# Good - broken into multiple lines
with open('/path/to/some/file/that/you/want/to/read') as file_1, \
     open('/path/to/some/file/that/you/want/to/write', 'w') as file_2:
    file_2.write(file_1.read())

# Better - use parentheses for implicit line continuation
with (
    open('/path/to/some/file/that/you/want/to/read') as file_1,
    open('/path/to/some/file/that/you/want/to/write', 'w') as file_2
):
    file_2.write(file_1.read())
```

## Blank Lines

- **Two** blank lines between top-level function and class definitions
- **One** blank line between method definitions inside a class
- Use blank lines sparingly within functions to indicate logical sections

```python
def top_level_function():
    pass


def another_top_level():
    pass


class MyClass:
    """Class docstring."""
    
    def method_one(self):
        pass
    
    def method_two(self):
        pass


def another_function():
    pass
```

## Imports

### Import Order

1. Standard library imports
2. Related third-party imports
3. Local application/library specific imports

```python
# Standard library
import os
import sys
from pathlib import Path

# Third-party
import requests
import pandas as pd

# Local
from mypackage import utils
from mypackage.models import User
```

### Import Formatting

```python
# Good - each import on separate line
import os
import sys
from subprocess import Popen, PIPE

# Bad - multiple imports on one line
import os, sys

# Good - explicit imports
from mymodule import MyClass, my_function

# Bad - wildcard imports
from mymodule import *
```

### Absolute vs Relative Imports

```python
# Good - absolute imports
import mypkg.sibling
from mypkg import sibling
from mypkg.sibling import example

# Acceptable - explicit relative imports
from . import sibling
from .sibling import example

# Bad - implicit relative imports (Python 2 style)
import sibling  # This might import the wrong module!
```

## Naming Conventions

### Package and Module Names

```python
# Good - short, lowercase
import mypackage
import my_module

# Bad
import MyPackage
import my-module  # Hyphens not allowed
```

### Class Names

```python
# Good - CapWords (PascalCase)
class MyClass:
    pass

class HttpRequest:
    pass

class UserAccount:
    pass

# Bad
class my_class:
    pass

class myClass:
    pass
```

### Function and Variable Names

```python
# Good - snake_case
def my_function():
    pass

user_name = "Alice"
total_count = 42

# Bad
def MyFunction():
    pass

def myFunction():
    pass

UserName = "Alice"  # Looks like a class
```

### Constants

```python
# Good - UPPER_CASE with underscores
MAX_CONNECTIONS = 100
DEFAULT_TIMEOUT = 30
PI = 3.14159

# Bad
maxConnections = 100
DefaultTimeout = 30
```

### Private/Internal Names

```python
# Single underscore - internal use
_internal_variable = 42

def _internal_function():
    pass


# Double underscore - name mangling for classes
class MyClass:
    def __init__(self):
        self.__private = 42  # Becomes _MyClass__private
    
    def __private_method(self):
        pass
```

## String Quotes

Be consistent. Pick single or double quotes and stick with it.

```python
# Good - consistent
print("Hello World")
print('Goodbye')
name = "Alice"
greeting = 'Hi'

# Also good - use different quotes to avoid escaping
message = "It's a nice day"
path = 'C:\\Users\\name\\file.txt'

# Triple quotes for docstrings and multiline strings
docstring = """This is a docstring."""
multiline = '''
Line 1
Line 2
Line 3
'''
```

## Whitespace

### Avoid Extraneous Whitespace

```python
# Good - no spaces immediately inside brackets
spam(ham[1], {eggs: 2})

# Bad
spam( ham[ 1 ], { eggs: 2 } )


# Good - no space before comma
foo = (0,)

# Bad
foo = (0, )


# Good - no space before colon in slices
ham[1:9], ham[1:9:3], ham[:9:3]

# Bad
ham[1: 9], ham[1 :9], ham[1:9 :3]


# Good - no space around = for keyword arguments
def complex(real, imag=0.0):
    return magic(r=real, i=imag)

# Bad
def complex(real, imag = 0.0):
    return magic(r = real, i = imag)
```

### Operator Spacing

```python
# Good - spaces around operators
x = 1
y = 2
long_variable = 3
i = i + 1
submitted += 1
x = x * 2 - 1
hypot2 = x * x + y * y
c = (a + b) * (a - b)

# Good - no spaces for keyword arguments or defaults
def function(default_parameter=5):
    pass

# Bad
i=i+1
submitted +=1
x = x*2 - 1
```

### Other Recommendations

```python
# Good - one space after comma
range(1, 11)
a = [1, 2, 3, 4]

# Bad
range(1,11)
a = [1,2,3,4]


# Good - no trailing whitespace
x = 1
y = 2

# Bad
x = 1 
y = 2  


# Good - single space around assignment in annotations
def func(x: int = 5):
    pass

# Bad
def func(x: int=5):
    pass
```

## Comments

### Block Comments

```python
# Good - complete sentences, proper capitalization
# Calculate the factorial of a number using recursion.
# This function assumes the input is a non-negative integer.
def factorial(n):
    if n == 0:
        return 1
    return n * factorial(n - 1)

# Bad - incomplete, lowercase
# calc factorial
def factorial(n):
    pass
```

### Inline Comments

```python
# Good - two spaces after code
x = x + 1  # Compensate for border

# Bad - too many spaces
x = x + 1    # Compensate

# Bad - obvious comment
x = x + 1  # Increment x

# Bad - same line as code block
if x > 0: x = x + 1  # Compensate
```

### Documentation Strings (Docstrings)

```python
def my_function():
    """Short one-line summary.
    
    More detailed description if needed. This can span
    multiple lines and should explain what the function
    does and how to use it.
    
    Args:
        param1: Description of param1
        param2: Description of param2
    
    Returns:
        Description of return value
    
    Raises:
        ValueError: When something is wrong
    """
    pass


class MyClass:
    """Class summary.
    
    Longer class description...
    
    Attributes:
        attr1: Description of attr1
        attr2: Description of attr2
    """
    
    def __init__(self):
        """Initialize MyClass."""
        self.attr1 = None
        self.attr2 = None
```

## Programming Recommendations

### Comparisons

```python
# Good - use 'is' for singletons
if x is None:
    pass

if x is not None:
    pass

# Bad - using '==' for None
if x == None:
    pass


# Good - use truthiness
if items:
    pass

if not items:
    pass

# Bad
if len(items) > 0:
    pass

if items == []:
    pass
```

### Boolean Operators

```python
# Good - use 'not in'
if x not in seq:
    pass

# Bad
if not x in seq:
    pass


# Good - use 'is not'
if x is not y:
    pass

# Bad
if not x is y:
    pass
```

### Return Statements

```python
# Good - be consistent
if condition:
    return True
return False

# Better - return boolean directly
return condition


# Good - return None explicitly if needed
def some_function():
    if not condition:
        return None
    return result
```

### Mutable Default Arguments

```python
# Bad - mutable default
def append_to(element, to=[]):
    to.append(element)
    return to

append_to(1)  # Returns [1]
append_to(2)  # Returns [1, 2] - surprise!


# Good - use None as default
def append_to(element, to=None):
    if to is None:
        to = []
    to.append(element)
    return to


# Good - immutable defaults are fine
def function_with_immutable(param=(1, 2, 3)):
    pass
```

### String Formatting

```python
name = "Alice"
age = 30

# Good - f-strings (Python 3.6+)
message = f"Hello, {name}! You are {age} years old."

# Acceptable - str.format()
message = "Hello, {}! You are {} years old.".format(name, age)

# Avoid - % formatting
message = "Hello, %s! You are %d years old." % (name, age)
```

### Type Comparison

```python
# Good - isinstance() for type checking
if isinstance(obj, int):
    pass

# Bad - direct type comparison
if type(obj) is int:
    pass


# Good - isinstance with tuple
def is_number(x):
    return isinstance(x, (int, float, complex))
```

### Exception Handling

```python
# Good - specific exception types
try:
    value = my_dict[key]
except KeyError:
    value = default

# Bad - bare except
except:  # Catches KeyboardInterrupt!
    pass

# Bad - catching Exception without need
except Exception:
    pass
```

### Context Managers

```python
# Good - use 'with' for resources
with open('file.txt', 'r') as f:
    content = f.read()

# Bad - manual resource management
f = open('file.txt', 'r')
content = f.read()
f.close()  # Might not execute if exception!
```

## Tools for Checking PEP 8

### linters

```bash
# flake8 - checks PEP 8 and more
pip install flake8
flake8 myfile.py

# pycodestyle - PEP 8 only
pip install pycodestyle
pycodestyle myfile.py

# pylint - comprehensive linting
pip install pylint
pylint myfile.py
```

### Formatters

```bash
# Ruff - extremely fast Python linter and formatter
pip install ruff
ruff format myfile.py

# autopep8 - fixes PEP 8 violations
pip install autopep8
autopep8 --in-place --aggressive myfile.py

# isort - sorts imports
pip install isort
isort myfile.py
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
```

## References

- PEP 8 Official: https://peps.python.org/pep-0008/
- Ruff Formatter: https://docs.astral.sh/ruff/
- Google Python Style Guide: https://google.github.io/styleguide/pyguide.html
