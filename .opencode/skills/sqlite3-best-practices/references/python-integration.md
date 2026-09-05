# Python SQLite3 Integration

Guide to using Python's sqlite3 module effectively.

## Connection Management

### Basic Connection

```python
import sqlite3

# Simple connection
conn = sqlite3.connect('database.db')

# Connection with timeout and isolation level
conn = sqlite3.connect(
    'database.db',
    timeout=30.0,          # Wait up to 30 seconds for locks
    isolation_level=None,   # Autocommit mode
    check_same_thread=False # For multi-threading
)

# Enable foreign keys immediately
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys = ON;")

# Don't forget to close!
conn.close()
```

### Context Manager (Recommended)

```python
# Connection as context manager
with sqlite3.connect('database.db') as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    results = cursor.fetchall()
    # Automatically commits on success
# Connection closed automatically
```

### Custom Context Manager

```python
from contextlib import contextmanager

@contextmanager
def get_db_connection(db_path: str, timeout: float = 30.0):
    """Context manager with proper setup."""
    conn = sqlite3.connect(db_path, timeout=timeout)
    try:
        # Always enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON;")
        # Use Row factory for dict-like access
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# Usage
with get_db_connection('app.db') as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    for row in cursor.fetchall():
        print(row['name'])  # Dict-like access
```

## Cursor Operations

### Creating a Cursor

```python
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Or using context manager
with conn:
    cursor = conn.cursor()
    # Operations...
```

### Executing Queries

```python
# Single query
cursor.execute("SELECT * FROM users WHERE id = 1")

# With parameters (safe from SQL injection)
cursor.execute(
    "SELECT * FROM users WHERE email = ?",
    ('user@example.com',)
)

# Multiple parameters
cursor.execute(
    "INSERT INTO users (email, name, age) VALUES (?, ?, ?)",
    ('user@example.com', 'John', 30)
)
```

### Fetching Results

```python
# fetchone() - Single row
cursor.execute("SELECT * FROM users WHERE id = ?", (1,))
row = cursor.fetchone()
if row:
    print(row)  # Tuple: (1, 'user@example.com', 'John', ...)

# fetchall() - All rows
cursor.execute("SELECT * FROM users LIMIT 10")
rows = cursor.fetchall()
for row in rows:
    print(row)

# fetchmany() - Batch rows
cursor.execute("SELECT * FROM users")
while True:
    rows = cursor.fetchmany(100)  # Get 100 at a time
    if not rows:
        break
    for row in rows:
        process(row)
```

## Parameterized Queries

### Question Mark Style (?)

```python
# Positional parameters
cursor.execute(
    "SELECT * FROM users WHERE status = ? AND age > ?",
    ('active', 18)
)

# Insert with parameters
user_data = ('alice@example.com', 'Alice', 25)
cursor.execute(
    "INSERT INTO users (email, name, age) VALUES (?, ?, ?)",
    user_data
)

# Update with parameters
cursor.execute(
    "UPDATE users SET name = ? WHERE id = ?",
    ('Alice Smith', 1)
)

# Delete with parameters
cursor.execute(
    "DELETE FROM users WHERE status = ?",
    ('deleted',)
)
```

### Named Placeholders (:name)

```python
# Named parameters (more readable)
cursor.execute("""
    SELECT * FROM users 
    WHERE status = :status AND age > :min_age
""", {
    'status': 'active',
    'min_age': 18
})

# Insert with named parameters
cursor.execute("""
    INSERT INTO users (email, name, age)
    VALUES (:email, :name, :age)
""", {
    'email': 'bob@example.com',
    'name': 'Bob',
    'age': 30
})
```

### executemany() for Batch Operations

```python
# Batch insert
users = [
    ('user1@example.com', 'User 1', 25),
    ('user2@example.com', 'User 2', 30),
    ('user3@example.com', 'User 3', 35),
]

cursor.executemany(
    "INSERT INTO users (email, name, age) VALUES (?, ?, ?)",
    users
)

# Batch with named parameters
users = [
    {'email': 'a@b.com', 'name': 'A', 'age': 20},
    {'email': 'c@d.com', 'name': 'B', 'age': 25},
]

cursor.executemany(
    "INSERT INTO users (email, name, age) VALUES (:email, :name, :age)",
    users
)

# From generator (memory efficient)
def user_generator():
    for i in range(10000):
        yield (f'user{i}@example.com', f'User {i}', 20 + i % 50)

cursor.executemany(
    "INSERT INTO users (email, name, age) VALUES (?, ?, ?)",
    user_generator()
)
```

## Row Factories

### sqlite3.Row (Dictionary-like)

```python
# Enable Row factory
conn.row_factory = sqlite3.Row

cursor = conn.cursor()
cursor.execute("SELECT id, email, name FROM users")

row = cursor.fetchone()
print(row['id'])      # By name
print(row[0])         # By index
print(row.keys())     # ['id', 'email', 'name']
print(dict(row))      # Convert to dict
```

### Custom Row Factory

```python
def dict_factory(cursor, row):
    """Return rows as dictionaries."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

conn.row_factory = dict_factory

cursor.execute("SELECT * FROM users")
for row in cursor.fetchall():
    print(row['email'])  # Dict access


# NamedTuple factory
from collections import namedtuple

def namedtuple_factory(cursor, row):
    """Return rows as namedtuples."""
    fields = [column[0] for column in cursor.description]
    cls = namedtuple("Row", fields)
    return cls._make(row)

conn.row_factory = namedtuple_factory
```

## Error Handling

### Exception Hierarchy

```python
import sqlite3

try:
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM nonexistent_table")
    
except sqlite3.OperationalError as e:
    # Database error (e.g., table doesn't exist, locked)
    print(f"Operational error: {e}")
    
except sqlite3.IntegrityError as e:
    # Constraint violation (unique, foreign key, check)
    print(f"Integrity error: {e}")
    
except sqlite3.ProgrammingError as e:
    # Programming error (e.g., wrong number of parameters)
    print(f"Programming error: {e}")
    
except sqlite3.DataError as e:
    # Data processing error
    print(f"Data error: {e}")
    
except sqlite3.Error as e:
    # Generic SQLite error
    print(f"SQLite error: {e}")
```

### Transaction Error Handling

```python
def safe_transaction(conn, operations):
    """Execute operations with proper error handling."""
    cursor = conn.cursor()
    
    try:
        cursor.execute("BEGIN;")
        
        for op in operations:
            cursor.execute(op['sql'], op.get('params', ()))
        
        cursor.execute("COMMIT;
        return True
        
    except sqlite3.IntegrityError as e:
        cursor.execute("ROLLBACK;")
        print(f"Integrity error, rolled back: {e}")
        return False
        
    except sqlite3.Error as e:
        cursor.execute("ROLLBACK;")
        print(f"Error, rolled back: {e}")
        raise
```

## Transactions

### Manual Transaction Control

```python
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

try:
    # Start transaction
    cursor.execute("BEGIN TRANSACTION;")
    
    # Multiple operations
    cursor.execute("INSERT INTO accounts ...")
    cursor.execute("UPDATE accounts ...")
    cursor.execute("INSERT INTO transactions ...")
    
    # Commit
    cursor.execute("COMMIT;")
    
except sqlite3.Error:
    # Rollback on error
    cursor.execute("ROLLBACK;")
    raise
finally:
    conn.close()
```

### Automatic Transactions

```python
# Using connection as context manager (auto-commit)
with sqlite3.connect('database.db') as conn:
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users ...")
    cursor.execute("INSERT INTO posts ...")
    # Commits automatically if no exception

# Using isolation_level=None (autocommit)
conn = sqlite3.connect('database.db', isolation_level=None)
cursor = conn.cursor()
cursor.execute("INSERT INTO users ...")  # Auto-committed
```

### Savepoints

```python
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

try:
    cursor.execute("BEGIN;")
    
    # Main operations
    cursor.execute("INSERT INTO orders ...")
    
    # Create savepoint
    cursor.execute("SAVEPOINT before_items;")
    
    try:
        # Risky operations
        for item in items:
            cursor.execute("INSERT INTO order_items ...")
    except sqlite3.Error:
        # Rollback to savepoint
        cursor.execute("ROLLBACK TO SAVEPOINT before_items;")
        # Continue with order (no items)
    
    cursor.execute("COMMIT;")
    
except sqlite3.Error:
    cursor.execute("ROLLBACK;")
    raise
```

## Type Converters

### Registering Converters

```python
import json
from datetime import datetime

# Convert datetime to/from ISO format
def adapt_datetime(ts):
    return ts.isoformat()

def convert_datetime(s):
    return datetime.fromisoformat(s.decode())

# Register adapters
sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("datetime", convert_datetime)

# Use in connection
detect_types=sqlite3.PARSE_DECLTYPES
conn = sqlite3.connect('database.db', detect_types=detect_types)

# Now datetime columns are automatically converted
```

### JSON Converter

```python
import json

# Store Python dict as JSON
def adapt_dict(d):
    return json.dumps(d)

def convert_dict(s):
    return json.loads(s.decode())

sqlite3.register_adapter(dict, adapt_dict)
sqlite3.register_converter("json", convert_dict)

# Usage
conn = sqlite3.connect(
    'database.db',
    detect_types=sqlite3.PARSE_DECLTYPES
)

cursor.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        name TEXT,
        settings json  -- Will be converted
    )
""")

settings = {'theme': 'dark', 'notifications': True}
cursor.execute(
    "INSERT INTO users (name, settings) VALUES (?, ?)",
    ('John', settings)  # Automatically converted to JSON
)
```

## Thread Safety

### Connection per Thread

```python
import threading
import sqlite3

class ThreadSafeDB:
    def __init__(self, db_path):
        self.db_path = db_path
        self.local = threading.local()
    
    def get_connection(self):
        """Get thread-local connection."""
        if not hasattr(self.local, 'connection'):
            self.local.connection = sqlite3.connect(self.db_path)
            self.local.connection.execute("PRAGMA foreign_keys = ON;")
        return self.local.connection
    
    def execute(self, sql, params=None):
        """Execute in thread-safe manner."""
        conn = self.get_connection()
        cursor = conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        conn.commit()
        return cursor
```

### Queue-based Access

```python
from queue import Queue
from threading import Thread

def db_worker(db_path, queue):
    """Worker thread for database access."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    
    while True:
        item = queue.get()
        if item is None:
            break
        
        sql, params, result_queue = item
        try:
            cursor = conn.execute(sql, params)
            result_queue.put(('ok', cursor.fetchall()))
        except Exception as e:
            result_queue.put(('error', str(e)))
        
        queue.task_done()

# Usage
queue = Queue()
worker = Thread(target=db_worker, args=('database.db', queue))
worker.start()

# Send query
result_queue = Queue()
queue.put(("SELECT * FROM users", (), result_queue))
status, result = result_queue.get()
```

## Best Practices

### 1. Always Use Context Managers

```python
# Good: Automatic cleanup
with sqlite3.connect('database.db') as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    # Commits automatically

# Good: Custom context manager
@contextmanager
def get_db():
    conn = sqlite3.connect('database.db')
    try:
        yield conn
        conn.commit()
    except:
        conn.rollback()
        raise
    finally:
        conn.close()
```

### 2. Enable Foreign Keys

```python
# Always enable foreign keys
conn = sqlite3.connect('database.db')
conn.execute("PRAGMA foreign_keys = ON;")
# Or in connection setup
```

### 3. Use Parameterized Queries

```python
# Good: Safe from SQL injection
cursor.execute("SELECT * FROM users WHERE email = ?", (email,))

# Bad: SQL injection vulnerability
cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")
```

### 4. Handle Errors Properly

```python
try:
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute("BEGIN;")
        # ... operations
        cursor.execute("COMMIT;")
except sqlite3.IntegrityError as e:
    # Handle constraint violation
    print(f"Data integrity error: {e}")
except sqlite3.Error as e:
    # Handle other SQLite errors
    print(f"Database error: {e}")
```

### 5. Use Row Factory for Readable Code

```python
conn.row_factory = sqlite3.Row

cursor.execute("SELECT id, name, email FROM users")
for row in cursor.fetchall():
    print(f"User: {row['name']} ({row['email']})")
```

## References

- Python sqlite3: https://docs.python.org/3/library/sqlite3.html
- DB-API 2.0: https://peps.python.org/pep-0249/
- Thread Safety: https://www.sqlite.org/threadsafe.html
