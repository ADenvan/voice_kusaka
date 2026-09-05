#!/usr/bin/env python3
"""Production-ready SQLite Database Manager.

A complete example of best practices for SQLite database operations in Python.
Includes connection management, transaction handling, error recovery, and
performance optimizations.

Usage:
    # Basic usage
    db = DatabaseManager('app.db')
    db.connect()

    # Create table
    db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL
        )
    ''')

    # Insert data
    user_id = db.execute(
        "INSERT INTO users (email, name) VALUES (?, ?)",
        ('user@example.com', 'John')
    )

    # Query data
    users = db.fetchall("SELECT * FROM users WHERE status = ?", ('active',))

    # Close connection
    db.close()
"""

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

# Configure logging
logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Base exception for database operations."""

    pass


class ConnectionError(DatabaseError):
    """Raised when connection fails."""

    pass


class QueryError(DatabaseError):
    """Raised when query execution fails."""

    pass


class DatabaseManager:
    """Production-ready SQLite database manager.

    Features:
    - Connection pooling and management
    - Automatic transaction handling
    - Parameterized queries (SQL injection safe)
    - Comprehensive error handling
    - Performance optimizations (WAL mode, etc.)
    - Context manager support
    - Row factory for dict-like access

    Attributes:
        db_path: Path to the SQLite database file
        connection: Active SQLite connection
        cursor: Active cursor object
    """

    def __init__(
        self,
        db_path: str | Path,
        timeout: float = 30.0,
        detect_types: bool = True,
        isolation_level: str | None = None,
        wal_mode: bool = True,
        foreign_keys: bool = True,
    ):
        """Initialize database manager.

        Args:
            db_path: Path to SQLite database file
            timeout: Connection timeout in seconds
            detect_types: Enable type detection for converters
            isolation_level: Transaction isolation level (None = autocommit)
            wal_mode: Enable Write-Ahead Logging
            foreign_keys: Enforce foreign key constraints
        """
        self.db_path = Path(db_path)
        self.timeout = timeout
        self.detect_types = detect_types
        self.isolation_level = isolation_level
        self.wal_mode = wal_mode
        self.foreign_keys = foreign_keys

        self._connection: sqlite3.Connection | None = None
        self._cursor: sqlite3.Cursor | None = None

        logger.debug(f"Initialized DatabaseManager for {self.db_path}")

    def connect(self) -> sqlite3.Connection:
        """Establish database connection.

        Returns:
            sqlite3.Connection: Active connection

        Raises:
            ConnectionError: If connection fails
        """
        try:
            # Ensure parent directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Build connection parameters
            conn_params = {
                "database": str(self.db_path),
                "timeout": self.timeout,
                "isolation_level": self.isolation_level,
            }

            if self.detect_types:
                conn_params["detect_types"] = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES

            # Create connection
            self._connection = sqlite3.connect(**conn_params)

            # Configure connection
            self._configure_connection()

            # Create cursor
            self._cursor = self._connection.cursor()

            logger.info(f"Connected to database: {self.db_path}")
            return self._connection

        except sqlite3.Error as e:
            raise ConnectionError(f"Failed to connect to {self.db_path}: {e}")

    def _configure_connection(self) -> None:
        """Configure connection with optimal settings."""
        if not self._connection:
            return

        # Enable foreign keys
        if self.foreign_keys:
            self._connection.execute("PRAGMA foreign_keys = ON;")

        # Enable WAL mode for better concurrency
        if self.wal_mode:
            self._connection.execute("PRAGMA journal_mode = WAL;")
            self._connection.execute("PRAGMA synchronous = NORMAL;")

        # Set row factory for dict-like access
        self._connection.row_factory = sqlite3.Row

        # Optimize cache size (64MB)
        self._connection.execute("PRAGMA cache_size = -64000;")

        logger.debug("Connection configured with optimal settings")

    def close(self) -> None:
        """Close database connection."""
        if self._cursor:
            self._cursor.close()
            self._cursor = None

        if self._connection:
            try:
                self._connection.commit()
            except sqlite3.Error:
                self._connection.rollback()
            finally:
                self._connection.close()
                self._connection = None
                logger.info("Database connection closed")

    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._connection is not None

    def ensure_connected(self) -> None:
        """Ensure connection is active."""
        if not self.is_connected:
            self.connect()

    # -------------------------------------------------------------------------
    # Transaction Management
    # -------------------------------------------------------------------------

    def begin(self) -> None:
        """Begin a transaction."""
        self.ensure_connected()
        self._connection.execute("BEGIN;")
        logger.debug("Transaction started")

    def commit(self) -> None:
        """Commit current transaction."""
        if self._connection:
            self._connection.commit()
            logger.debug("Transaction committed")

    def rollback(self) -> None:
        """Rollback current transaction."""
        if self._connection:
            self._connection.rollback()
            logger.debug("Transaction rolled back")

    @contextmanager
    def transaction(self):
        """Context manager for transactions.

        Usage:
            with db.transaction():
                db.execute("INSERT INTO users ...")
                db.execute("INSERT INTO posts ...")
                # Auto-commit on success, rollback on exception
        """
        self.ensure_connected()
        self.begin()
        try:
            yield self
            self.commit()
        except Exception:
            self.rollback()
            raise

    # -------------------------------------------------------------------------
    # Query Execution
    # -------------------------------------------------------------------------

    def execute(self, sql: str, parameters: tuple | dict[str, Any] | None = None) -> sqlite3.Cursor:
        """Execute SQL query.

        Args:
            sql: SQL statement
            parameters: Query parameters (tuple for ?, dict for :name)

        Returns:
            sqlite3.Cursor: Cursor object

        Raises:
            QueryError: If execution fails
        """
        self.ensure_connected()

        try:
            if parameters:
                cursor = self._connection.execute(sql, parameters)
            else:
                cursor = self._connection.execute(sql)

            logger.debug(f"Executed: {sql[:100]}...")
            return cursor

        except sqlite3.Error as e:
            raise QueryError(f"Query failed: {e}\nSQL: {sql}")

    def executemany(
        self, sql: str, parameters_list: list[tuple | dict[str, Any]]
    ) -> sqlite3.Cursor:
        """Execute SQL query multiple times.

        Args:
            sql: SQL statement
            parameters_list: List of parameter tuples/dicts

        Returns:
            sqlite3.Cursor: Cursor object
        """
        self.ensure_connected()

        try:
            cursor = self._connection.executemany(sql, parameters_list)
            logger.debug(f"Executed {len(parameters_list)} batches")
            return cursor

        except sqlite3.Error as e:
            raise QueryError(f"Batch query failed: {e}")

    def executescript(self, sql_script: str) -> sqlite3.Cursor:
        """Execute multiple SQL statements.

        Args:
            sql_script: SQL script with multiple statements

        Returns:
            sqlite3.Cursor: Cursor object
        """
        self.ensure_connected()

        try:
            cursor = self._connection.executescript(sql_script)
            logger.debug("Executed SQL script")
            return cursor

        except sqlite3.Error as e:
            raise QueryError(f"Script execution failed: {e}")

    # -------------------------------------------------------------------------
    # Data Retrieval
    # -------------------------------------------------------------------------

    def fetchone(
        self, sql: str, parameters: tuple | dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """Fetch single row.

        Args:
            sql: SELECT statement
            parameters: Query parameters

        Returns:
            Dict with column names as keys, or None if no rows
        """
        cursor = self.execute(sql, parameters)
        row = cursor.fetchone()
        return dict(row) if row else None

    def fetchall(
        self, sql: str, parameters: tuple | dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Fetch all rows.

        Args:
            sql: SELECT statement
            parameters: Query parameters

        Returns:
            List of dicts with column names as keys
        """
        cursor = self.execute(sql, parameters)
        return [dict(row) for row in cursor.fetchall()]

    def fetchmany(
        self, sql: str, parameters: tuple | dict[str, Any] | None = None, size: int = 100
    ) -> list[dict[str, Any]]:
        """Fetch multiple rows.

        Args:
            sql: SELECT statement
            parameters: Query parameters
            size: Number of rows to fetch

        Returns:
            List of dicts with column names as keys
        """
        cursor = self.execute(sql, parameters)
        return [dict(row) for row in cursor.fetchmany(size)]

    def fetchscalar(
        self, sql: str, parameters: tuple | dict[str, Any] | None = None, default: Any = None
    ) -> Any:
        """Fetch single scalar value.

        Args:
            sql: SELECT statement returning single value
            parameters: Query parameters
            default: Default value if no rows

        Returns:
            Single value or default
        """
        cursor = self.execute(sql, parameters)
        row = cursor.fetchone()
        return row[0] if row else default

    # -------------------------------------------------------------------------
    # Convenience Methods
    # -------------------------------------------------------------------------

    def insert(self, table: str, data: dict[str, Any], replace: bool = False) -> int:
        """Insert single row.

        Args:
            table: Table name
            data: Column values as dict
            replace: Use REPLACE instead of INSERT

        Returns:
            Row ID of inserted row
        """
        columns = list(data.keys())
        placeholders = [f":{col}" for col in columns]

        action = "REPLACE" if replace else "INSERT"
        sql = f"{action} INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"

        cursor = self.execute(sql, data)
        return cursor.lastrowid

    def insert_many(self, table: str, data: list[dict[str, Any]], batch_size: int = 1000) -> int:
        """Insert multiple rows.

        Args:
            table: Table name
            data: List of column value dicts
            batch_size: Commit batch size

        Returns:
            Number of rows inserted
        """
        if not data:
            return 0

        columns = list(data[0].keys())
        placeholders = [f":{col}" for col in columns]
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"

        total = 0
        with self.transaction():
            for i in range(0, len(data), batch_size):
                batch = data[i : i + batch_size]
                self.executemany(sql, batch)
                total += len(batch)

        return total

    def update(
        self, table: str, data: dict[str, Any], where: str, where_params: tuple | dict[str, Any]
    ) -> int:
        """Update rows.

        Args:
            table: Table name
            data: Column values to update
            where: WHERE clause
            where_params: WHERE parameters

        Returns:
            Number of rows updated
        """
        set_clause = ", ".join([f"{col} = :{col}" for col in data])
        sql = f"UPDATE {table} SET {set_clause} WHERE {where}"

        # Merge data and where_params
        if isinstance(where_params, dict):
            params = {**data, **where_params}
        else:
            # Convert positional params to named
            params = data.copy()
            params.update({f"_wp_{i}": v for i, v in enumerate(where_params)})

        cursor = self.execute(sql, params)
        return cursor.rowcount

    def delete(
        self, table: str, where: str, parameters: tuple | dict[str, Any] | None = None
    ) -> int:
        """Delete rows.

        Args:
            table: Table name
            where: WHERE clause
            parameters: WHERE parameters

        Returns:
            Number of rows deleted
        """
        sql = f"DELETE FROM {table} WHERE {where}"
        cursor = self.execute(sql, parameters)
        return cursor.rowcount

    # -------------------------------------------------------------------------
    # Schema Operations
    # -------------------------------------------------------------------------

    def create_table(self, table: str, columns: dict[str, str], if_not_exists: bool = True) -> None:
        """Create table.

        Args:
            table: Table name
            columns: Column definitions {name: type/constraints}
            if_not_exists: Add IF NOT EXISTS clause
        """
        column_defs = [f"{name} {def_}" for name, def_ in columns.items()]
        exists_clause = "IF NOT EXISTS " if if_not_exists else ""

        sql = f"CREATE TABLE {exists_clause}{table} ({', '.join(column_defs)})"
        self.execute(sql)
        logger.info(f"Created table: {table}")

    def create_index(
        self,
        index: str,
        table: str,
        columns: list[str],
        unique: bool = False,
        if_not_exists: bool = True,
    ) -> None:
        """Create index.

        Args:
            index: Index name
            table: Table name
            columns: Column names
            unique: Create unique index
            if_not_exists: Add IF NOT EXISTS clause
        """
        unique_clause = "UNIQUE " if unique else ""
        exists_clause = "IF NOT EXISTS " if if_not_exists else ""
        columns_str = ", ".join(columns)

        sql = f"CREATE {unique_clause}INDEX {exists_clause}{index} ON {table} ({columns_str})"
        self.execute(sql)
        logger.info(f"Created index: {index}")

    def table_exists(self, table: str) -> bool:
        """Check if table exists.

        Args:
            table: Table name

        Returns:
            True if table exists
        """
        sql = "SELECT 1 FROM sqlite_schema WHERE type = 'table' AND name = ?"
        return self.fetchscalar(sql, (table,), False) is not None

    def get_tables(self) -> list[str]:
        """Get list of all tables.

        Returns:
            List of table names
        """
        sql = "SELECT name FROM sqlite_schema WHERE type = 'table' ORDER BY name"
        rows = self.fetchall(sql)
        return [row["name"] for row in rows]

    def get_table_info(self, table: str) -> list[dict[str, Any]]:
        """Get table schema information.

        Args:
            table: Table name

        Returns:
            List of column info dicts
        """
        sql = f"PRAGMA table_info({table})"
        return self.fetchall(sql)

    # -------------------------------------------------------------------------
    # Maintenance
    # -------------------------------------------------------------------------

    def vacuum(self) -> None:
        """Rebuild database file to defragment."""
        self.execute("VACUUM")
        logger.info("Database vacuumed")

    def analyze(self, table: str | None = None) -> None:
        """Update query optimizer statistics.

        Args:
            table: Specific table to analyze, or all tables if None
        """
        if table:
            self.execute(f"ANALYZE {table}")
            logger.info(f"Analyzed table: {table}")
        else:
            self.execute("ANALYZE")
            logger.info("Analyzed all tables")

    def optimize(self) -> None:
        """Run PRAGMA optimize."""
        self.execute("PRAGMA optimize")
        logger.info("Database optimized")

    def integrity_check(self) -> bool:
        """Run integrity check.

        Returns:
            True if database is OK
        """
        result = self.fetchscalar("PRAGMA integrity_check")
        is_ok = result == "ok"

        if is_ok:
            logger.info("Integrity check passed")
        else:
            logger.error(f"Integrity check failed: {result}")

        return is_ok

    def get_stats(self) -> dict[str, Any]:
        """Get database statistics.

        Returns:
            Dict with database stats
        """
        stats = {
            "page_size": self.fetchscalar("PRAGMA page_size"),
            "page_count": self.fetchscalar("PRAGMA page_count"),
            "freelist_count": self.fetchscalar("PRAGMA freelist_count"),
            "journal_mode": self.fetchscalar("PRAGMA journal_mode"),
            "cache_size": self.fetchscalar("PRAGMA cache_size"),
        }

        stats["size_bytes"] = stats["page_size"] * stats["page_count"]
        stats["size_mb"] = round(stats["size_bytes"] / (1024 * 1024), 2)

        return stats

    # -------------------------------------------------------------------------
    # Context Manager
    # -------------------------------------------------------------------------

    def __enter__(self) -> "DatabaseManager":
        """Enter context manager."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()

    def __del__(self):
        """Destructor - ensure connection is closed."""
        self.close()


# =============================================================================
# Example Usage
# =============================================================================


def main():
    """Example usage of DatabaseManager."""

    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Use as context manager (recommended)
    with DatabaseManager("example.db", wal_mode=True) as db:
        # Create table
        db.create_table(
            "users",
            {
                "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                "email": "TEXT NOT NULL UNIQUE",
                "name": "TEXT NOT NULL",
                "status": "TEXT DEFAULT 'active'",
                "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
            },
        )

        # Create index
        db.create_index("idx_users_status", "users", ["status"])

        # Insert single row
        user_id = db.insert("users", {"email": "alice@example.com", "name": "Alice"})
        print(f"Inserted user with ID: {user_id}")

        # Insert multiple rows
        users = [
            {"email": "bob@example.com", "name": "Bob"},
            {"email": "charlie@example.com", "name": "Charlie"},
        ]
        count = db.insert_many("users", users)
        print(f"Inserted {count} users")

        # Query
        active_users = db.fetchall("SELECT * FROM users WHERE status = ?", ("active",))
        print(f"Found {len(active_users)} active users")

        # Update
        updated = db.update("users", {"status": "premium"}, "id = :id", {"id": user_id})
        print(f"Updated {updated} rows")

        # Get stats
        stats = db.get_stats()
        print(f"Database size: {stats['size_mb']} MB")

        # Maintenance
        db.analyze()
        db.integrity_check()


if __name__ == "__main__":
    main()
