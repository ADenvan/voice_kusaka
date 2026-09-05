# SQLite Schema Design Guide

Comprehensive guide for designing robust SQLite database schemas.

## Data Types

SQLite uses dynamic typing with storage classes:

### Storage Classes

| Class | Description | Use For |
|-------|-------------|---------|
| `NULL` | Missing value | Optional fields |
| `INTEGER` | Whole numbers | IDs, counts, timestamps |
| `REAL` | Floating point | Prices, measurements |
| `TEXT` | UTF-8/UTF-16 strings | Names, descriptions, JSON |
| `BLOB` | Binary data | Images, files (avoid if possible) |

### Type Affinity

```sql
-- INTEGER affinity
CREATE TABLE t1 (
    id INTEGER PRIMARY KEY,  -- Stored as INTEGER
    count INT,               -- INTEGER affinity
    qty INTEGER,             -- INTEGER affinity
    rowid ROWID              -- INTEGER affinity
);

-- TEXT affinity
CREATE TABLE t2 (
    name TEXT,               -- TEXT affinity
    desc VARCHAR(100),       -- TEXT affinity
    char CHARACTER(20),      -- TEXT affinity
    json JSON                -- TEXT affinity (SQLite 3.45+)
);

-- REAL affinity
CREATE TABLE t3 (
    price REAL,              -- REAL affinity
    amount DOUBLE,           -- REAL affinity
    value FLOAT              -- REAL affinity
);

-- NUMERIC affinity (flexible)
CREATE TABLE t4 (
    num NUMERIC,             -- NUMERIC affinity
    dec DECIMAL(10,2),       -- NUMERIC affinity
    bool BOOLEAN             -- NUMERIC affinity (0/1)
);
```

### Best Practice: Explicit Types

```sql
-- Good: Clear intent with explicit types
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    price REAL CHECK (price >= 0),
    quantity INTEGER DEFAULT 0,
    description TEXT,
    active BOOLEAN DEFAULT 1,
    metadata TEXT  -- JSON stored as TEXT
);
```

## Primary Keys

### INTEGER PRIMARY KEY (Recommended)

```sql
-- Best: Auto-incrementing integer
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL
);

-- Benefits:
-- - Uses internal ROWID (fastest access)
-- - 64-bit signed integer
-- - Auto-increment guaranteed unique
-- - Most efficient storage
```

### Without ROWID

```sql
-- Use for non-integer natural keys
CREATE TABLE countries (
    code TEXT PRIMARY KEY,  -- 'US', 'UK', etc.
    name TEXT NOT NULL,
    population INTEGER
) WITHOUT ROWID;

-- When to use WITHOUT ROWID:
-- - Non-integer primary keys
-- - Composite primary keys
-- - Very wide rows (> 2KB)
```

### Composite Primary Keys

```sql
-- Junction table for many-to-many
CREATE TABLE user_roles (
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    granted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    granted_by INTEGER,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
) WITHOUT ROWID;  -- Important for composite keys
```

## Constraints

### NOT NULL

```sql
CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,           -- Required field
    content TEXT NOT NULL,
    published BOOLEAN NOT NULL 
        DEFAULT 0,                 -- Default value
    author_id INTEGER NOT NULL     -- Required relationship
);
```

### UNIQUE

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,           -- Single column unique
    username TEXT NOT NULL UNIQUE,
    phone TEXT UNIQUE,                     -- Nullable unique
    
    -- Multi-column unique constraint
    CONSTRAINT uq_name_email UNIQUE (first_name, last_name, email)
);

-- Alternative syntax
CREATE UNIQUE INDEX idx_unique_email 
ON users(email) WHERE deleted_at IS NULL;  -- Partial unique index
```

### CHECK Constraints

```sql
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    price REAL NOT NULL 
        CHECK (price >= 0),                  -- Non-negative
    
    quantity INTEGER NOT NULL 
        CHECK (quantity >= 0),               -- Non-negative
    
    status TEXT NOT NULL 
        CHECK (status IN ('active', 'inactive', 'discontinued')),
    
    discount_percent INTEGER 
        CHECK (discount_percent BETWEEN 0 AND 100),
    
    sku TEXT 
        CHECK (length(sku) >= 3 
               AND sku REGEXP '^[A-Z]{2}-[0-9]{4}$')  -- Pattern validation
);
```

### DEFAULT Values

```sql
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    status TEXT NOT NULL 
        DEFAULT 'pending',
    
    total REAL NOT NULL 
        DEFAULT 0.0,
    
    created_at TEXT NOT NULL 
        DEFAULT CURRENT_TIMESTAMP,
    
    updated_at TEXT NOT NULL 
        DEFAULT CURRENT_TIMESTAMP,
    
    is_urgent BOOLEAN 
        DEFAULT 0,
    
    metadata TEXT 
        DEFAULT '{}'  -- Empty JSON object
);
```

## Foreign Keys

### Basic Foreign Keys

```sql
CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Remember to enable:
-- PRAGMA foreign_keys = ON;
```

### Foreign Key Actions

```sql
CREATE TABLE comments (
    id INTEGER PRIMARY KEY,
    post_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    
    -- CASCADE: Delete comments when post is deleted
    FOREIGN KEY (post_id) 
        REFERENCES posts(id) 
        ON DELETE CASCADE,
    
    -- SET NULL: Keep comment but remove user reference
    FOREIGN KEY (user_id) 
        REFERENCES users(id) 
        ON DELETE SET NULL
);

-- All actions:
-- ON DELETE CASCADE     - Delete dependent rows
-- ON DELETE SET NULL    - Set FK to NULL
-- ON DELETE SET DEFAULT - Set FK to DEFAULT
-- ON DELETE RESTRICT    - Prevent deletion (default)
-- ON DELETE NO ACTION   - Like RESTRICT but deferred
-- ON UPDATE CASCADE     - Update FK when PK changes
```

### Self-Referencing Foreign Keys

```sql
-- Hierarchical categories
CREATE TABLE categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    parent_id INTEGER,
    
    FOREIGN KEY (parent_id) 
        REFERENCES categories(id) 
        ON DELETE CASCADE
);

-- Hierarchical comments (nested replies)
CREATE TABLE comments (
    id INTEGER PRIMARY KEY,
    post_id INTEGER NOT NULL,
    parent_id INTEGER,  -- Reply to another comment
    content TEXT NOT NULL,
    
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES comments(id) ON DELETE CASCADE
);
```

## Normalization

### First Normal Form (1NF)

```sql
-- Bad: Multiple values in one column
CREATE TABLE orders_bad (
    id INTEGER PRIMARY KEY,
    items TEXT  -- '1,2,3,4' - comma-separated IDs
);

-- Good: Separate table
CREATE TABLE order_items (
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    
    PRIMARY KEY (order_id, product_id),
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);
```

### Second Normal Form (2NF)

```sql
-- Bad: Partial dependency
CREATE TABLE order_items_bad (
    order_id INTEGER,
    product_id INTEGER,
    product_name TEXT,  -- Depends only on product_id
    quantity INTEGER,
    PRIMARY KEY (order_id, product_id)
);

-- Good: Separate into tables
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    price REAL NOT NULL
);

CREATE TABLE order_items (
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    
    PRIMARY KEY (order_id, product_id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);
```

### Third Normal Form (3NF)

```sql
-- Bad: Transitive dependency
CREATE TABLE employees_bad (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    department_id INTEGER,
    department_name TEXT,  -- Depends on department_id, not id
    department_location TEXT
);

-- Good: Separate department info
CREATE TABLE departments (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    location TEXT
);

CREATE TABLE employees (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    department_id INTEGER,
    
    FOREIGN KEY (department_id) REFERENCES departments(id)
);
```

## Common Schema Patterns

### Soft Delete Pattern

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    status TEXT NOT NULL 
        DEFAULT 'active'
        CHECK (status IN ('active', 'suspended', 'deleted')),
    deleted_at TEXT,  -- ISO-8601 timestamp
    deleted_by INTEGER,
    
    -- Ensure deleted_at is set when status is 'deleted'
    CHECK (
        (status != 'deleted' AND deleted_at IS NULL) OR
        (status = 'deleted' AND deleted_at IS NOT NULL)
    )
);

-- Index for filtering active users
CREATE INDEX idx_users_active 
ON users(status, deleted_at) 
WHERE status = 'active';

-- Query active users
SELECT * FROM users WHERE status = 'active';

-- Query all (including deleted) - admin only
SELECT * FROM users;
```

### Audit Trail Pattern

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL,
    name TEXT NOT NULL,
    
    -- Audit columns
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER,
    version INTEGER NOT NULL DEFAULT 1,
    
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (updated_by) REFERENCES users(id)
);

-- Auto-update trigger
CREATE TRIGGER update_users_timestamp
AFTER UPDATE ON users
BEGIN
    UPDATE users 
    SET updated_at = CURRENT_TIMESTAMP,
        version = version + 1
    WHERE id = NEW.id;
END;

-- Audit log table
CREATE TABLE users_audit (
    audit_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    old_data TEXT,  -- JSON of previous values
    new_data TEXT,  -- JSON of new values
    changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    changed_by INTEGER
);

-- Audit trigger
CREATE TRIGGER audit_users_update
AFTER UPDATE ON users
BEGIN
    INSERT INTO users_audit (user_id, action, old_data, new_data)
    VALUES (
        NEW.id,
        'UPDATE',
        json_object(
            'email', OLD.email,
            'name', OLD.name
        ),
        json_object(
            'email', NEW.email,
            'name', NEW.name
        )
    );
END;
```

### State Machine Pattern

```sql
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    total REAL NOT NULL,
    
    -- State machine
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN (
            'draft',
            'pending_payment',
            'paid',
            'processing',
            'shipped',
            'delivered',
            'cancelled',
            'refunded'
        )),
    
    -- State timestamps
    draft_at TEXT DEFAULT CURRENT_TIMESTAMP,
    pending_payment_at TEXT,
    paid_at TEXT,
    processing_at TEXT,
    shipped_at TEXT,
    delivered_at TEXT,
    cancelled_at TEXT,
    refunded_at TEXT,
    
    -- Valid state transitions
    CHECK (
        (status = 'draft' AND draft_at IS NOT NULL) OR
        (status = 'pending_payment' AND pending_payment_at IS NOT NULL) OR
        (status = 'paid' AND paid_at IS NOT NULL) OR
        (status = 'processing' AND processing_at IS NOT NULL) OR
        (status = 'shipped' AND shipped_at IS NOT NULL) OR
        (status = 'delivered' AND delivered_at IS NOT NULL) OR
        (status = 'cancelled' AND cancelled_at IS NOT NULL) OR
        (status = 'refunded' AND refunded_at IS NOT NULL)
    )
);

-- State history
CREATE TABLE order_status_history (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    from_status TEXT,
    to_status TEXT NOT NULL,
    changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    changed_by INTEGER,
    notes TEXT,
    
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);
```

### Tag System Pattern

```sql
-- Normalized tags
CREATE TABLE tags (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    color TEXT DEFAULT '#808080',
    usage_count INTEGER DEFAULT 0
);

-- Many-to-many relationship
CREATE TABLE post_tags (
    post_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    added_by INTEGER,
    
    PRIMARY KEY (post_id, tag_id),
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- Find posts by tag
SELECT p.* 
FROM posts p
JOIN post_tags pt ON p.id = pt.post_id
JOIN tags t ON pt.tag_id = t.id
WHERE t.name = 'python';

-- Find related tags
SELECT t2.name, COUNT(*) as co_occurrence
FROM post_tags pt1
JOIN post_tags pt2 ON pt1.post_id = pt2.post_id AND pt1.tag_id != pt2.tag_id
JOIN tags t2 ON pt2.tag_id = t2.id
WHERE pt1.tag_id = (SELECT id FROM tags WHERE name = 'python')
GROUP BY t2.id
ORDER BY co_occurrence DESC
LIMIT 10;
```

## Date and Time Handling

### Recommended Formats

```sql
-- ISO-8601 format (recommended)
CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    event_date TEXT,        -- '2024-01-15'
    event_datetime TEXT,    -- '2024-01-15 14:30:00'
    event_iso TEXT          -- '2024-01-15T14:30:00Z'
);

-- Unix timestamp (INTEGER)
CREATE TABLE events_ts (
    id INTEGER PRIMARY KEY,
    created_at INTEGER  -- Unix epoch seconds
);

-- Date functions
SELECT 
    date('now'),                          -- Current date
    datetime('now'),                      -- Current datetime
    strftime('%Y-%m-%d', 'now'),          -- Formatted date
    julianday('2024-01-15') - julianday('2024-01-01'),  -- Days between
    unixepoch('now')                      -- Unix timestamp
```

### Date Indexes

```sql
-- Index for date range queries
CREATE INDEX idx_events_date 
ON events(event_date);

-- Query date ranges efficiently
SELECT * FROM events
WHERE event_date BETWEEN '2024-01-01' AND '2024-01-31'
ORDER BY event_date;
```

## JSON Support (SQLite 3.38+)

### Storing JSON

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL,
    -- Flexible metadata as JSON
    preferences TEXT CHECK (json_valid(preferences)),
    settings TEXT CHECK (json_valid(settings))
);

-- Insert JSON
INSERT INTO users (email, preferences, settings) VALUES (
    'user@example.com',
    '{"theme": "dark", "notifications": true}',
    '{"language": "en", "timezone": "UTC"}'
);
```

### Querying JSON

```sql
-- Extract values
SELECT 
    email,
    json_extract(preferences, '$.theme') as theme,
    json_extract(settings, '$.language') as language
FROM users;

-- Filter by JSON value
SELECT * FROM users
WHERE json_extract(preferences, '$.theme') = 'dark';

-- Update JSON
UPDATE users 
SET preferences = json_set(preferences, '$.theme', 'light')
WHERE id = 1;

-- Check if key exists
SELECT * FROM users
WHERE json_type(preferences, '$.notifications') IS NOT NULL;
```

## Schema Migration

### Adding Columns

```sql
-- Add new column
ALTER TABLE users ADD COLUMN phone TEXT;

-- Add with constraints (SQLite 3.37+)
ALTER TABLE users ADD COLUMN age INTEGER CHECK (age >= 0);

-- Add with default
ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active';
```

### Creating Tables with Migration

```sql
-- Step 1: Create new table with updated schema
CREATE TABLE users_v2 (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    phone TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Step 2: Copy data
INSERT INTO users_v2 (id, email, name, created_at)
SELECT id, email, name, created_at FROM users;

-- Step 3: Drop old table
DROP TABLE users;

-- Step 4: Rename new table
ALTER TABLE users_v2 RENAME TO users;

-- Step 5: Recreate indexes
CREATE INDEX idx_users_email ON users(email);
```

## References

- SQLite Data Types: https://www.sqlite.org/datatype3.html
- CREATE TABLE: https://www.sqlite.org/lang_createtable.html
- Foreign Keys: https://www.sqlite.org/foreignkeys.html
- JSON1 Extension: https://www.sqlite.org/json1.html
