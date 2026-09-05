# SQLite Query Optimization

Guide to writing efficient SQL queries and optimizing database performance.

## Index Strategy

### When to Create Indexes

```sql
-- Create indexes on columns used in:
-- 1. WHERE clauses
-- 2. JOIN conditions
-- 3. ORDER BY clauses
-- 4. GROUP BY clauses

-- Basic single-column index
CREATE INDEX idx_users_email ON users(email);

-- Index for range queries
CREATE INDEX idx_orders_date ON orders(created_at);

-- Index for sorting
CREATE INDEX idx_posts_created ON posts(created_at DESC);

-- Unique index
CREATE UNIQUE INDEX idx_users_username ON users(username);
```

### Composite Indexes

```sql
-- Multi-column index (order matters!)
CREATE INDEX idx_orders_user_status 
ON orders(user_id, status);

-- Most selective column first
CREATE INDEX idx_products_category_price 
ON products(category_id, price);

-- Covering index (includes all queried columns)
CREATE INDEX idx_users_list 
ON users(status, created_at DESC, email, name);

-- Partial index (filtered)
CREATE INDEX idx_active_users 
ON users(email) 
WHERE status = 'active';
```

### Index Best Practices

```sql
-- Good: Index for common query pattern
SELECT * FROM users WHERE email = 'test@example.com';
-- Index: CREATE INDEX idx_users_email ON users(email);

-- Good: Composite index matches query
SELECT * FROM orders 
WHERE user_id = 123 AND status = 'pending';
-- Index: CREATE INDEX idx_orders_user_status ON orders(user_id, status);

-- Good: Covering index avoids table lookup
SELECT email, name FROM users WHERE status = 'active';
-- Index: CREATE INDEX idx_users_active ON users(status) INCLUDE (email, name);
```

## Query Analysis

### EXPLAIN QUERY PLAN

```sql
-- Analyze query execution
EXPLAIN QUERY PLAN
SELECT * FROM users WHERE email = 'test@example.com';

-- Good output:
-- SEARCH TABLE users USING INDEX idx_users_email (email=?)

-- Bad output:
-- SCAN TABLE users  -- Full table scan!
```

### Understanding Output

```sql
-- SCAN TABLE - Full table scan (slow for large tables)
EXPLAIN QUERY PLAN SELECT * FROM users;
-- SCAN TABLE users

-- SEARCH TABLE - Uses index (fast)
EXPLAIN QUERY PLAN SELECT * FROM users WHERE id = 1;
-- SEARCH TABLE users USING INTEGER PRIMARY KEY (rowid=?)

-- USING INDEX - Index scan
EXPLAIN QUERY PLAN SELECT * FROM users WHERE email = 'a@b.com';
-- SEARCH TABLE users USING INDEX idx_users_email (email=?)

-- USING COVERING INDEX - Index-only scan (fastest)
EXPLAIN QUERY PLAN SELECT email FROM users WHERE email = 'a@b.com';
-- SEARCH TABLE users USING COVERING INDEX idx_users_email (email=?)
```

## SELECT Optimization

### Explicit Column Lists

```sql
-- Good: Only select needed columns
SELECT id, email, name FROM users WHERE status = 'active';

-- Bad: SELECT * retrieves unnecessary data
SELECT * FROM users WHERE status = 'active';
```

### LIMIT and Pagination

```sql
-- Offset pagination (simple but slower for large offsets)
SELECT * FROM users
ORDER BY id
LIMIT 10 OFFSET 1000;

-- Keyset pagination (faster for large datasets)
SELECT * FROM users
WHERE id > 1000  -- Last seen ID from previous page
ORDER BY id
LIMIT 10;

-- Cursor-based pagination
SELECT * FROM users
WHERE (created_at, id) > ('2024-01-01', 100)
ORDER BY created_at, id
LIMIT 10;
```

### EXISTS vs COUNT

```sql
-- Good: EXISTS stops at first match
SELECT 1 FROM users WHERE status = 'active' LIMIT 1;

-- Bad: COUNT scans entire table
SELECT COUNT(*) FROM users WHERE status = 'active';

-- Check if any rows exist
SELECT EXISTS(
    SELECT 1 FROM orders WHERE user_id = 123
) as has_orders;
```

## JOIN Optimization

### JOIN Types

```sql
-- INNER JOIN: Only matching rows
SELECT u.name, p.title
FROM users u
INNER JOIN posts p ON u.id = p.user_id;

-- LEFT JOIN: All left table rows, null for non-matches
SELECT u.name, COUNT(p.id) as post_count
FROM users u
LEFT JOIN posts p ON u.id = p.user_id
GROUP BY u.id, u.name;

-- Use appropriate JOIN for your needs
-- INNER JOIN is faster when you don't need unmatched rows
```

### JOIN Performance

```sql
-- Good: Index on JOIN column
CREATE INDEX idx_posts_user ON posts(user_id);

SELECT u.*, p.title
FROM users u
JOIN posts p ON u.id = p.user_id
WHERE u.status = 'active';

-- Good: Filter before JOIN
SELECT u.*, p.title
FROM (
    SELECT * FROM users WHERE status = 'active'
) u
JOIN posts p ON u.id = p.user_id;
```

## Aggregation Optimization

### GROUP BY

```sql
-- Good: Indexed GROUP BY column
CREATE INDEX idx_orders_user ON orders(user_id);

SELECT user_id, COUNT(*) as order_count
FROM orders
GROUP BY user_id;

-- Good: Filtering before aggregation
SELECT user_id, COUNT(*) as order_count
FROM orders
WHERE created_at >= '2024-01-01'
GROUP BY user_id;
```

### HAVING vs WHERE

```sql
-- Good: WHERE filters before aggregation (faster)
SELECT user_id, COUNT(*) as order_count
FROM orders
WHERE status = 'completed'  -- Filter rows first
GROUP BY user_id
HAVING COUNT(*) > 5;         -- Then filter groups

-- Bad: HAVING for row filtering (slower)
SELECT user_id, COUNT(*) as order_count
FROM orders
GROUP BY user_id
HAVING status = 'completed';  -- Wrong! Filters after aggregation
```

### Window Functions

```sql
-- Row numbering
SELECT 
    id,
    name,
    salary,
    ROW_NUMBER() OVER (ORDER BY salary DESC) as rank
FROM employees;

-- Running totals
SELECT 
    date,
    amount,
    SUM(amount) OVER (ORDER BY date) as running_total
FROM transactions;

-- Partitioned calculations
SELECT 
    department,
    name,
    salary,
    AVG(salary) OVER (PARTITION BY department) as dept_avg,
    salary - AVG(salary) OVER (PARTITION BY department) as diff
FROM employees;

-- Lead/Lag for time series
SELECT 
    date,
    value,
    LAG(value) OVER (ORDER BY date) as prev_value,
    value - LAG(value) OVER (ORDER BY date) as change
FROM metrics;
```

## Subquery Optimization

### Correlated vs Non-Correlated

```sql
-- Non-correlated: Executed once (faster)
SELECT * FROM orders
WHERE user_id IN (
    SELECT id FROM users WHERE status = 'premium'
);

-- Correlated: Executed for each row (slower)
SELECT * FROM orders o
WHERE EXISTS (
    SELECT 1 FROM users u 
    WHERE u.id = o.user_id AND u.status = 'premium'
);

-- Often better to use JOIN
SELECT o.* FROM orders o
JOIN users u ON o.user_id = u.id
WHERE u.status = 'premium';
```

### CTEs (Common Table Expressions)

```sql
-- Readable and reusable
WITH active_users AS (
    SELECT id, email, name
    FROM users
    WHERE status = 'active'
),
user_stats AS (
    SELECT 
        user_id,
        COUNT(*) as post_count,
        MAX(created_at) as last_post
    FROM posts
    GROUP BY user_id
)
SELECT 
    au.id,
    au.email,
    au.name,
    COALESCE(us.post_count, 0) as posts,
    us.last_post
FROM active_users au
LEFT JOIN user_stats us ON au.id = us.user_id;

-- Recursive CTE for hierarchical data
WITH RECURSIVE category_tree AS (
    -- Anchor: root categories
    SELECT id, name, parent_id, 0 as level
    FROM categories
    WHERE parent_id IS NULL
    
    UNION ALL
    
    -- Recursive: child categories
    SELECT c.id, c.name, c.parent_id, ct.level + 1
    FROM categories c
    JOIN category_tree ct ON c.parent_id = ct.id
)
SELECT * FROM category_tree
ORDER BY level, name;
```

## Full-Text Search

### FTS5 Setup

```sql
-- Create FTS5 virtual table
CREATE VIRTUAL TABLE articles_fts USING fts5(
    title,
    content,
    content='articles',  -- Link to main table
    content_rowid='id'
);

-- Populate with data
INSERT INTO articles_fts(rowid, title, content)
SELECT id, title, content FROM articles;

-- Keep in sync with triggers
CREATE TRIGGER articles_ai AFTER INSERT ON articles BEGIN
    INSERT INTO articles_fts(rowid, title, content)
    VALUES (new.id, new.title, new.content);
END;

CREATE TRIGGER articles_ad AFTER DELETE ON articles BEGIN
    INSERT INTO articles_fts(articles_fts, rowid, title, content)
    VALUES ('delete', old.id, old.title, old.content);
END;

CREATE TRIGGER articles_au AFTER UPDATE ON articles BEGIN
    INSERT INTO articles_fts(articles_fts, rowid, title, content)
    VALUES ('delete', old.id, old.title, old.content);
    INSERT INTO articles_fts(rowid, title, content)
    VALUES (new.id, new.title, new.content);
END;
```

### FTS5 Queries

```sql
-- Basic search
SELECT * FROM articles_fts WHERE articles_fts MATCH 'python sqlite';

-- Phrase search
SELECT * FROM articles_fts WHERE articles_fts MATCH '"machine learning"';

-- Prefix search
SELECT * FROM articles_fts WHERE articles_fts MATCH 'data*';

-- Boolean search
SELECT * FROM articles_fts WHERE articles_fts MATCH 'python AND sqlite NOT mysql';

-- With ranking
SELECT 
    a.*,
    rank
FROM articles_fts 
JOIN articles a ON articles_fts.rowid = a.id
WHERE articles_fts MATCH 'python tutorial'
ORDER BY rank;

-- Highlight matches
SELECT 
    highlight(articles_fts, 0, '<b>', '</b>') as title,
    highlight(articles_fts, 1, '<b>', '</b>') as snippet
FROM articles_fts
WHERE articles_fts MATCH 'sqlite';
```

## Anti-Patterns to Avoid

### SELECT *

```sql
-- Bad: Retrieves all columns unnecessarily
SELECT * FROM users WHERE id = 1;

-- Good: Explicit columns
SELECT id, email, name FROM users WHERE id = 1;
```

### Functions on Indexed Columns

```sql
-- Bad: Function prevents index usage
SELECT * FROM users WHERE UPPER(email) = 'TEST@EXAMPLE.COM';

-- Good: Index can be used
SELECT * FROM users WHERE email = 'test@example.com';

-- Alternative: Store normalized data
SELECT * FROM users WHERE email_normalized = 'test@example.com';
```

### Implicit Conversions

```sql
-- Bad: Implicit conversion prevents index usage
SELECT * FROM users WHERE id = '123';  -- id is INTEGER

-- Good: Matching types
SELECT * FROM users WHERE id = 123;
```

### OR Conditions

```sql
-- Bad: OR prevents index usage
SELECT * FROM users 
WHERE email = 'a@b.com' OR username = 'alice';

-- Good: Use UNION
SELECT * FROM users WHERE email = 'a@b.com'
UNION
SELECT * FROM users WHERE username = 'alice';
```

### OFFSET for Large Pagination

```sql
-- Bad: OFFSET 1000000 is slow
SELECT * FROM posts ORDER BY id LIMIT 10 OFFSET 1000000;

-- Good: Keyset pagination
SELECT * FROM posts 
WHERE id > 1000000 
ORDER BY id 
LIMIT 10;
```

## Query Performance Checklist

Before deploying queries:

- [ ] Use `EXPLAIN QUERY PLAN` to verify index usage
- [ ] Avoid `SELECT *` - list only needed columns
- [ ] Use appropriate indexes on WHERE, JOIN, ORDER BY columns
- [ ] Filter early with WHERE before aggregation
- [ ] Use EXISTS instead of COUNT for existence checks
- [ ] Consider LIMIT for large result sets
- [ ] Use transactions for multiple write operations
- [ ] Avoid functions on indexed columns
- [ ] Use parameterized queries (not string concatenation)
- [ ] Test with realistic data volumes

## References

- Query Planner: https://www.sqlite.org/queryplanner.html
- OPTIMIZE: https://www.sqlite.org/lang_analyze.html
- FTS5: https://www.sqlite.org/fts5.html
- CTEs: https://www.sqlite.org/lang_with.html
