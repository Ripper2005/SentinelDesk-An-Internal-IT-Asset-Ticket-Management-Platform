# Task 5: Indexing, justified by measurement

Index under test:

```sql
CREATE INDEX idx_tickets_type_status ON tickets(ticket_type, status);
```

Query under test (`reports/report_type_status_having.sql`):

```sql
SELECT ticket_type, status, COUNT(*) AS ticket_count
FROM tickets
GROUP BY ticket_type, status
HAVING COUNT(*) >= 3
ORDER BY ticket_type, status;
```

## `EXPLAIN QUERY PLAN` before creating the index

```
(7, 0, 216, 'SCAN tickets')
(9, 0, 0, 'USE TEMP B-TREE FOR GROUP BY')
```

## `EXPLAIN QUERY PLAN` after creating the index

```
(7, 0, 213, 'SCAN tickets USING COVERING INDEX idx_tickets_type_status')
```

## What changed, in one sentence

Before the index, SQLite had to scan the whole `tickets` table and build a
temporary B-tree to sort rows into `(ticket_type, status)` groups. After
creating `idx_tickets_type_status`, the index already stores rows in
exactly that grouped order and contains every column the query touches, so
SQLite reads the covering index directly and the
`USE TEMP B-TREE FOR GROUP BY` step disappears entirely.
