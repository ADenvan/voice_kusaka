---
name: sqlite3-best-practices
description: |
    Build optimized SQLite databases for pay_b payroll system.
    Use when designing schemas, writing queries, optimizing performance,
    or implementing data persistence for Employee/Timesheet entities.
origin: ArDEN
metadata:
  author: pay_b team
  version: "2.0"
---

# SQLite3 Best Practices for pay_b

pay_b-specific SQLite guidelines for the desktop payroll management system.

## When to use this skill

- Designing or changing `employees` / `timesheets` schema
- Writing payroll queries (salary calculation, hours aggregation)
- Implementing repository methods in `app/database/repositories.py`
- Migrating database schemas with SQLite limitations
- Performance tuning queries with `EXPLAIN QUERY PLAN`

## Project Structure

```
app/database/
  connection.py      # DatabaseConnection singleton (pay_b.db)
  models.py            # Employee, Timesheet dataclasses
  repositories.py      # EmployeeRepository, TimesheetRepository
```

## Quick Start

### Database Setup

```python
import sqlite3
from pathlib import Path

from app.database.connection import DatabaseConnection

# Initialise singleton connection
conn = DatabaseConnection(db_path=Path("pay_b.db")).get_connection()

# Create tables (if not exists)
conn.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        hourly_rate REAL NOT NULL CHECK (hourly_rate > 0),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
""")

conn.execute("""
    CREATE TABLE IF NOT EXISTS timesheets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        work_date TEXT NOT NULL,
        hours_worked REAL NOT NULL CHECK (hours_worked > 0 AND hours_worked <= 24),
        FOREIGN KEY (employee_id) REFERENCES employees(id)
            ON DELETE CASCADE
    );
""")

# Indexes for common payroll queries
conn.execute("CREATE INDEX IF NOT EXISTS idx_timesheets_employee_date ON timesheets(employee_id, work_date);")
conn.execute("CREATE INDEX IF NOT EXISTS idx_employees_name ON employees(full_name);")
```

### Repository Pattern (pay_b style)

```python
import sqlite3
from collections.abc import Sequence

from app.database.models import Employee, Timesheet


class EmployeeRepository:
    """Repository for Employee CRUD operations."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get_by_id(self, employee_id: int) -> Employee | None:
        """Fetch an employee by primary key."""
        row = self._conn.execute(
            "SELECT id, full_name, hourly_rate, created_at FROM employees WHERE id = ?",
            (employee_id,),
        ).fetchone()
        if row is None:
            return None
        return Employee(
            id=row["id"],
            full_name=row["full_name"],
            hourly_rate=row["hourly_rate"],
            created_at=row["created_at"],
        )

    def list_all(self) -> Sequence[Employee]:
        """Return all employees ordered by creation time (descending)."""
        cursor = self._conn.execute(
            "SELECT id, full_name, hourly_rate, created_at FROM employees ORDER BY created_at DESC"
        )
        return [
            Employee(
                id=row["id"],
                full_name=row["full_name"],
                hourly_rate=row["hourly_rate"],
                created_at=row["created_at"],
            )
            for row in cursor.fetchall()
        ]

    def create(self, full_name: str, hourly_rate: float) -> int:
        """Create employee and return ID."""
        cursor = self._conn.execute(
            "INSERT INTO employees (full_name, hourly_rate) VALUES (?, ?)",
            (full_name, hourly_rate),
        )
        self._conn.commit()
        return cursor.lastrowid


class TimesheetRepository:
    """Repository for Timesheet CRUD operations."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get_by_id(self, timesheet_id: int) -> Timesheet | None:
        """Fetch a timesheet entry by primary key."""
        row = self._conn.execute(
            "SELECT id, employee_id, work_date, hours_worked FROM timesheets WHERE id = ?",
            (timesheet_id,),
        ).fetchone()
        if row is None:
            return None
        return Timesheet(
            id=row["id"],
            employee_id=row["employee_id"],
            work_date=row["work_date"],
            hours_worked=row["hours_worked"],
        )

    def list_by_employee(self, employee_id: int) -> Sequence[Timesheet]:
        """Return all timesheets for a given employee."""
        cursor = self._conn.execute(
            """SELECT id, employee_id, work_date, hours_worked
               FROM timesheets
               WHERE employee_id = ?
               ORDER BY work_date DESC""",
            (employee_id,),
        )
        return [
            Timesheet(
                id=row["id"],
                employee_id=row["employee_id"],
                work_date=row["work_date"],
                hours_worked=row["hours_worked"],
            )
            for row in cursor.fetchall()
        ]

    def create(self, employee_id: int, work_date: str, hours_worked: float) -> int:
        """Create timesheet entry and return ID."""
        cursor = self._conn.execute(
            "INSERT INTO timesheets (employee_id, work_date, hours_worked) VALUES (?, ?, ?)",
            (employee_id, work_date, hours_worked),
        )
        self._conn.commit()
        return cursor.lastrowid
```

## Core Principles

### 1. Schema Design (pay_b Domain)

```sql
-- employees: core entity
CREATE TABLE employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    hourly_rate REAL NOT NULL CHECK (hourly_rate > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- timesheets: child entity with FK
CREATE TABLE timesheets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    work_date TEXT NOT NULL,  -- ISO-8601: '2024-01-15'
    hours_worked REAL NOT NULL CHECK (hours_worked > 0 AND hours_worked <= 24),
    FOREIGN KEY (employee_id) REFERENCES employees(id)
        ON DELETE CASCADE
);
```

### 2. Always Use Parameterized Queries

**Never** use f-strings for SQL in pay_b:

```python
# BAD - SQL injection vulnerability
name = "O'Brien"
cursor.execute(f"SELECT * FROM employees WHERE full_name = '{name}'")

# GOOD - Parameterized query
cursor.execute(
    "SELECT * FROM employees WHERE full_name = ?",
    (name,)
)
```

### 3. Enable Foreign Keys (DatabaseConnection already does this)

```python
conn = DatabaseConnection().get_connection()
# PRAGMA foreign_keys = ON; is already set
```

### 4. Use Transactions for Multi-Step Operations

```python
def create_employee_with_timesheet(
    conn: sqlite3.Connection,
    full_name: str,
    hourly_rate: float,
    work_date: str,
    hours_worked: float,
) -> tuple[int, int]:
    """Create employee and their first timesheet atomically."""
    try:
        conn.execute("BEGIN;")

        emp_repo = EmployeeRepository(conn)
        emp_id = emp_repo.create(full_name, hourly_rate)

        ts_repo = TimesheetRepository(conn)
        ts_id = ts_repo.create(emp_id, work_date, hours_worked)

        conn.execute("COMMIT;")
        return emp_id, ts_id

    except sqlite3.Error:
        conn.execute("ROLLBACK;")
        raise
```

### 5. Payroll-Specific Indexes

```sql
-- Employee name lookups
CREATE INDEX idx_employees_name ON employees(full_name);

-- Timesheet queries by employee and date range
CREATE INDEX idx_timesheets_employee_date ON timesheets(employee_id, work_date);

-- Date-only queries (e.g., "who worked today?")
CREATE INDEX idx_timesheets_work_date ON timesheets(work_date);
```

## Payroll Query Patterns

### Calculate Monthly Salary

```sql
SELECT
    e.id,
    e.full_name,
    e.hourly_rate,
    SUM(t.hours_worked) AS total_hours,
    ROUND(e.hourly_rate * SUM(t.hours_worked), 2) AS monthly_salary
FROM employees e
INNER JOIN timesheets t ON e.id = t.employee_id
WHERE t.work_date BETWEEN '2024-01-01' AND '2024-01-31'
GROUP BY e.id, e.full_name, e.hourly_rate;
```

### Employee Hours by Date Range

```sql
SELECT
    e.full_name,
    t.work_date,
    t.hours_worked
FROM employees e
INNER JOIN timesheets t ON e.id = t.employee_id
WHERE t.work_date BETWEEN ? AND ?
ORDER BY e.full_name, t.work_date;
```

### Total Payroll Cost per Period

```sql
SELECT
    ROUND(SUM(e.hourly_rate * t.hours_worked), 2) AS total_payroll_cost
FROM employees e
INNER JOIN timesheets t ON e.id = t.employee_id
WHERE t.work_date BETWEEN ? AND ?;
```

## DDL Workflow (SQLite Limitations)

### Supported directly
- `ALTER TABLE ADD COLUMN`
- `ALTER TABLE RENAME TABLE`
- `CREATE TABLE` / `DROP TABLE`

### Not supported — use rebuild pattern
SQLite does **not** support:
- `ALTER TABLE DROP COLUMN` (before 3.35.0)
- `ALTER TABLE MODIFY COLUMN` (never)

**Rebuild pattern for pay_b:**

```sql
BEGIN;

-- 1. Create new table with desired schema
CREATE TABLE employees_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    hourly_rate REAL NOT NULL CHECK (hourly_rate > 0),
    email TEXT,  -- new column
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. Copy data (fill new columns with defaults)
INSERT INTO employees_new (id, full_name, hourly_rate, email, created_at)
    SELECT id, full_name, hourly_rate, NULL, created_at FROM employees;

-- 3. Drop old table
DROP TABLE employees;

-- 4. Rename new table
ALTER TABLE employees_new RENAME TO employees;

COMMIT;
```

**After rebuild, always update:**
- `app/database/models.py` — add/modify dataclass fields
- `app/database/repositories.py` — update SELECT/INSERT queries

## Python Integration Patterns

### Connection via Singleton

```python
from app.database.connection import DatabaseConnection

conn = DatabaseConnection().get_connection()
repo = EmployeeRepository(conn)
employees = repo.list_all()
```

### Row Factory (already enabled)

```python
# DatabaseConnection sets row_factory = sqlite3.Row
row = conn.execute("SELECT * FROM employees WHERE id = ?", (1,)).fetchone()
name = row["full_name"]  # dict-like access
```

### Error Handling

```python
import sqlite3

try:
    repo.create("John Doe", 25.0)
except sqlite3.IntegrityError as exc:
    logger.error("Database integrity error: %s", exc)
    raise
except sqlite3.Error as exc:
    logger.error("Database error: %s", exc)
    raise
```

## Query Optimization

### Use EXPLAIN QUERY PLAN

```sql
EXPLAIN QUERY PLAN
SELECT e.full_name, SUM(t.hours_worked)
FROM employees e
INNER JOIN timesheets t ON e.id = t.employee_id
WHERE t.work_date BETWEEN '2024-01-01' AND '2024-01-31'
GROUP BY e.id;

-- Look for:
-- SEARCH TABLE employees USING PRIMARY KEY (id=?)
-- SEARCH TABLE timesheets USING INDEX idx_timesheets_employee_date
```

### Avoid Full Table Scans

```sql
-- Bad: no index on work_date
SELECT * FROM timesheets WHERE work_date = '2024-01-15';
-- → SCAN TABLE timesheets

-- Good: with index
-- idx_timesheets_work_date exists
-- → SEARCH TABLE timesheets USING INDEX idx_timesheets_work_date
```

## Date Handling

Store dates as **ISO-8601 TEXT** (`YYYY-MM-DD`):

```sql
-- Sortable, comparable, range queries work naturally
SELECT * FROM timesheets
WHERE work_date BETWEEN '2024-01-01' AND '2024-01-31'
ORDER BY work_date DESC;
```

## References

- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [Python sqlite3](https://docs.python.org/3/library/sqlite3.html)
- pay_b `app/database/connection.py` — singleton pattern
- pay_b `app/database/models.py` — dataclass models
- pay_b `app/database/repositories.py` — repository implementations
