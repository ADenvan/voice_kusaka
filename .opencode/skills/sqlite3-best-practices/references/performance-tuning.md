# SQLite Performance Tuning

Advanced techniques for optimizing SQLite database performance.

## PRAGMA Settings

### Journal Mode

```sql
-- DELETE mode (default): Journal file deleted after commit
PRAGMA journal_mode = DELETE;

-- TRUNCATE mode: Journal file truncated (faster on some systems)
PRAGMA journal_mode = TRUNCATE;

-- PERSIST mode: Journal file header overwritten
PRAGMA journal_mode = PERSIST;

-- MEMORY mode: Journal in RAM (fast but not crash-safe)
PRAGMA journal_mode = MEMORY;

-- WAL mode (recommended): Write-Ahead Logging
PRAGMA journal_mode = WAL;
-- Benefits:
-- - Readers don't block writers
-- - Writers don't block readers
-- - Better concurrency
-- - Often faster in practice
```

### Synchronous Mode

```sql
-- FULL (default): Sync after each write (safest, slowest)
PRAGMA synchronous = FULL;

-- NORMAL: Sync at critical moments (good balance)
PRAGMA synchronous = NORMAL;

-- OFF: No syncing (fastest, risk of corruption)
PRAGMA synchronous = OFF;
-- Only use in development or temporary databases
```

### Cache Size

```sql
-- Set cache size in pages (default: 2000 pages)
PRAGMA cache_size = 10000;        -- 10000 pages
PRAGMA cache_size = -64000;       -- 64MB (negative = KB)

-- For large databases, increase cache
PRAGMA cache_size = -131072;      -- 128MB

-- Check current cache size
PRAGMA cache_size;
```

### Page Size

```sql
-- Default: 4096 bytes
-- Options: 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536

-- Must be set before creating tables
PRAGMA page_size = 4096;

-- For large BLOBs, use larger pages
PRAGMA page_size = 8192;

-- Vacuum to apply page size change
PRAGMA page_size = 8192;
VACUUM;
```

### Temporary Storage

```sql
-- DEFAULT: Based on compile-time setting
PRAGMA temp_store = DEFAULT;

-- FILE: Use temporary files (default)
PRAGMA temp_store = FILE;

-- MEMORY: Use RAM for temp tables and indices
PRAGMA temp_store = MEMORY;

-- For complex queries with large temp data
PRAGMA temp_store = FILE;
PRAGMA temp_store_directory = '/fast/ssd/tmp';
```

## WAL Mode Deep Dive

### Enabling WAL

```sql
-- Switch to WAL mode (persistent)
PRAGMA journal_mode = WAL;

-- Check current mode
PRAGMA journal_mode;
-- Returns: wal, delete, truncate, persist, memory, off
```

### WAL Checkpointing

```sql
-- Automatic checkpoint (default: 1000 pages)
PRAGMA wal_autocheckpoint = 1000;

-- Manual checkpoint
PRAGMA wal_checkpoint;           -- PASSIVE (default)
PRAGMA wal_checkpoint(PASSIVE);  -- Non-blocking
PRAGMA wal_checkpoint(FULL);     -- Block until complete
PRAGMA wal_checkpoint(RESTART);  -- Restart with blocking
PRAGMA wal_checkpoint(TRUNCATE); -- Truncate WAL file

-- Check WAL size
PRAGMA wal_checkpoint;
-- Returns: busy, log, checkpointed
```

### WAL Configuration

```sql
-- Checkpoint threshold (pages)
PRAGMA wal_autocheckpoint = 1000;

-- For high write load, increase threshold
PRAGMA wal_autocheckpoint = 5000;

-- Or disable auto-checkpoint and do manually
PRAGMA wal_autocheckpoint = 0;
-- Then periodically: PRAGMA wal_checkpoint(TRUNCATE);
```

## Memory Mapping

### mmap Configuration

```sql
-- Enable memory mapping (0 = disabled)
PRAGMA mmap_size = 30000000000;  -- 30GB (or 0 to disable)

-- For read-heavy workloads
PRAGMA mmap_size = 268435456;    -- 256MB

-- Check current mmap size
PRAGMA mmap_size;
```

### Benefits of mmap

```sql
-- Faster read operations (no system calls)
-- Better OS caching
-- Reduced memory copies

-- Enable mmap
PRAGMA mmap_size = 1073741824;  -- 1GB

-- Best for:
-- - Read-heavy workloads
-- - Large databases
-- - When database fits in RAM
```

## Query Optimization

### ANALYZE Command

```sql
-- Collect statistics for query optimizer
ANALYZE;

-- Analyze specific table
ANALYZE users;

-- Analyze specific index
ANALYZE sqlite_schema;

-- Statistics stored in sqlite_stat1 table
SELECT * FROM sqlite_stat1;
```

### OPTIMIZE Pragma

```sql
-- SQLite 3.18+: Optimize database
PRAGMA optimize;

-- With specific analysis level
PRAGMA optimize(0x10002);  -- Analyze all tables

-- Run periodically (e.g., daily)
-- Or before important queries
```

## Bulk Operations

### Fast Inserts

```python
import sqlite3

conn = sqlite3.connect('database.db')
conn.execute("PRAGMA journal_mode = WAL;")
conn.execute("PRAGMA synchronous = NORMAL;")

# Method 1: executemany()
data = [(i, f'user{i}@example.com') for i in range(10000)]
conn.executemany(
    "INSERT INTO users (id, email) VALUES (?, ?)",
    data
)

# Method 2: Single transaction
conn.execute("BEGIN;")
cursor = conn.cursor()
for item in data:
    cursor.execute("INSERT INTO users (id, email) VALUES (?, ?)", item)
conn.execute("COMMIT;")

# Method 3: INSERT with VALUES list (SQLite 3.7.11+)
# Multiple rows in single INSERT
conn.execute("""
    INSERT INTO users (id, email) VALUES 
    (1, 'a@b.com'),
    (2, 'c@d.com'),
    (3, 'e@f.com')
""")
```

### Disabling Indexes for Bulk Load

```sql
-- For very large imports:

-- 1. Drop indexes
DROP INDEX idx_users_email;
DROP INDEX idx_users_name;

-- 2. Import data
-- ... bulk insert ...

-- 3. Recreate indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_name ON users(name);

-- 4. Analyze
ANALYZE;
```

## Database Maintenance

### VACUUM

```sql
-- Rebuild database file (defragment)
VACUUM;

-- Benefits:
-- - Removes free space
-- - Defragments data
-- - Can reduce file size
-- - Resets ROWIDs (unless INTEGER PRIMARY KEY)

-- Vacuum into new file
VACUUM INTO 'backup.db';

-- Note: Requires temporary disk space (~same as database size)
```

### REINDEX

```sql
-- Rebuild all indexes
REINDEX;

-- Rebuild specific index
REINDEX idx_users_email;

-- Rebuild indexes for table
REINDEX users;

-- Use after collation changes or corruption
```

### Integrity Check

```sql
-- Quick check
PRAGMA integrity_check;

-- Full check (slower)
PRAGMA integrity_check(10);  -- Max 10 errors

-- Check specific table
PRAGMA integrity_check(users);

-- Foreign key check
PRAGMA foreign_key_check;
PRAGMA foreign_key_check(users);
```

## Read Optimization

### Read-Only Mode

```python
import sqlite3

# Open in read-only mode
conn = sqlite3.connect('file:database.db?mode=ro', uri=True)

# Benefits:
# - No locking overhead
# - Multiple readers without conflict
# - Cannot accidentally modify
```

### Immutable Databases

```python
# For completely static databases
conn = sqlite3.connect('file:database.db?immutable=1', uri=True)

# Benefits:
# - No locking at all
# - Maximum read performance
# - Assumes database never changes
```

## Write Optimization

### Deferred Foreign Keys

```sql
-- Check foreign keys at commit, not immediately
PRAGMA defer_foreign_keys = ON;

-- Useful for:
-- - Circular references
-- - Self-referencing tables
-- - Complex insert order
```

### Exclusive Locking

```sql
-- Lock database for exclusive access
PRAGMA locking_mode = EXCLUSIVE;

-- Reduces locking overhead
-- Best for single-writer scenarios
-- Must close all connections to release
```

### Write-Ahead Logging Tuning

```sql
-- For write-heavy workloads:

PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA wal_autocheckpoint = 5000;  -- Less frequent checkpoints
PRAGMA cache_size = -131072;        -- 128MB cache

-- Manually checkpoint during low activity
PRAGMA wal_checkpoint(TRUNCATE);
```

## Connection Pooling

### Simple Connection Pool

```python
import sqlite3
from queue import Queue
from threading import Lock

class ConnectionPool:
    def __init__(self, db_path, max_connections=5):
        self.db_path = db_path
        self.max_connections = max_connections
        self._pool = Queue(max_connections)
        self._lock = Lock()
        self._initialized = False
        
    def initialize(self):
        """Create initial connections."""
        with self._lock:
            if not self._initialized:
                for _ in range(self.max_connections):
                    conn = sqlite3.connect(self.db_path)
                    conn.execute("PRAGMA foreign_keys = ON;")
                    self._pool.put(conn)
                self._initialized = True
    
    def get_connection(self):
        """Get connection from pool."""
        if not self._initialized:
            self.initialize()
        return self._pool.get()
    
    def release_connection(self, conn):
        """Return connection to pool."""
        self._pool.put(conn)
    
    def close_all(self):
        """Close all connections."""
        while not self._pool.empty():
            conn = self._pool.get()
            conn.close()

# Usage
pool = ConnectionPool('database.db', max_connections=10)
conn = pool.get_connection()
try:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
finally:
    pool.release_connection(conn)
```

## Monitoring

### Performance Metrics

```sql
-- Page count and size
PRAGMA page_count;
PRAGMA page_size;
PRAGMA freelist_count;  -- Free pages

-- Cache statistics
PRAGMA cache_size;

-- WAL statistics
PRAGMA wal_checkpoint;

-- Database size in bytes
SELECT page_count * page_size as size_bytes 
FROM pragma_page_count(), pragma_page_size();
```

### Query Timing

```python
import sqlite3
import time

conn = sqlite3.connect('database.db')
conn.execute("PRAGMA optimize;")

# Time a query
start = time.time()
cursor = conn.execute("SELECT * FROM large_table WHERE ...")
results = cursor.fetchall()
elapsed = time.time() - start
print(f"Query took {elapsed:.3f}s")

# Use EXPLAIN QUERY PLAN
plan = conn.execute("EXPLAIN QUERY PLAN SELECT ...").fetchall()
for row in plan:
    print(row)
```

## Production Checklist

Before deploying to production:

- [ ] Enable WAL mode: `PRAGMA journal_mode = WAL;`
- [ ] Set appropriate synchronous mode: `PRAGMA synchronous = NORMAL;`
- [ ] Configure cache size: `PRAGMA cache_size = -64000;` (64MB)
- [ ] Enable foreign keys: `PRAGMA foreign_keys = ON;`
- [ ] Run ANALYZE: `ANALYZE;`
- [ ] Verify indexes with `EXPLAIN QUERY PLAN`
- [ ] Test backup/restore procedures
- [ ] Monitor database size and growth
- [ ] Set up automated VACUUM if needed
- [ ] Test under expected load

## Configuration Templates

### Read-Heavy Workload

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = -131072;      -- 128MB
PRAGMA mmap_size = 268435456;     -- 256MB
PRAGMA temp_store = MEMORY;
```

### Write-Heavy Workload

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = -65536;       -- 64MB
PRAGMA wal_autocheckpoint = 5000;
PRAGMA locking_mode = NORMAL;
```

### Balanced Workload

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = -64000;       -- 64MB
PRAGMA mmap_size = 134217728;     -- 128MB
PRAGMA temp_store = FILE;
```

## References

- PRAGMA: https://www.sqlite.org/pragma.html
- WAL Mode: https://www.sqlite.org/wal.html
- Query Planner: https://www.sqlite.org/queryplanner.html
- Optimization: https://www.sqlite.org/optoverview.html
