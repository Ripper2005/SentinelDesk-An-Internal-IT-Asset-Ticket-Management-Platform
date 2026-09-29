# SentinelDesk

My capstone project: a small internal IT asset and ticket management
platform, built to replace a spreadsheet that got out of hand. It's plain
Python + SQLite using only the standard library (`sqlite3`, `threading`,
`abc`, `datetime`), so there is nothing to install and no accounts or
external services involved.

What's in the repo:

- `engine.py`: the domain model (an abstract `Ticket` class with three
  subclasses: `IncidentTicket`, `ServiceRequestTicket`,
  `MaintenanceTicket`) plus `HelpdeskEngine`, which loads the database
  into dicts/sets for fast in-memory lookups
- `schema.sql`, `seed_data.sql`: the 4-table schema (3NF) and the seed
  dataset
- `repository.py`: the write path with real transactions, plus a small
  demo proving atomicity
- `run_concurrency_experiment.py`: the two-threads-on-`reopen_count`
  experiment
- `reports/`: the seven SQL report queries
- `INDEXING_NOTES.md`, `DESIGN.md`: the index measurements and the design
  doc

## Setup

You need Python 3.10+ (I used 3.14, SQLite 3.50). Build the seeded database
first:

```bash
python -c "import sqlite3; c = sqlite3.connect('sentineldesk.db'); c.executescript(open('schema.sql').read()); c.executescript(open('seed_data.sql').read()); c.close()"
```

Quick sanity check on row counts:

```bash
python -c "import sqlite3; c = sqlite3.connect('sentineldesk.db'); [print(t, c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]) for t in ('employees','assets','tickets','ticket_status_history')]"
```

```
employees 12
assets 18
tickets 30
ticket_status_history 50
```

## Part 1: domain model and the in-memory engine

```bash
python engine.py
```

```
employees: 12
assets: 18
tickets[Open]: 10
tickets[InProgress]: 6
tickets[Resolved]: 7
tickets[Closed]: 7
ticket_type_seen: ['incident', 'maintenance', 'service_request']
('service_request','Open'): 7
('incident','Open'): 3
ticket 1 age at 2026-07-10: 8
notify(IncidentTicket): 5 steps
notify(ServiceRequestTicket): 4 steps
notify(MaintenanceTicket): 5 steps
Ticket() direct instantiation -> TypeError: Can't instantiate abstract class Ticket without an implementation for abstract method 'resolution_checklist'
```

So the numbers line up with the spec: 12 employees, 18 assets, tickets
split 10/6/7/7 across the four statuses, `('service_request','Open')` = 7
and `('incident','Open')` = 3, `age_in_days('2026-07-10')` = 8 for the
ticket created on 2026-07-02, `notify()` works on all three subclasses,
and calling `Ticket(...)` directly fails with `TypeError` since it's
abstract.

## Task 2: transactions (atomicity)

```bash
python repository.py
```

This runs against a throwaway copy of `sentineldesk.db`, so the real
seeded database doesn't get changed by the demo. Output:

```
== successful update_ticket_status(ticket 2, 'InProgress') ==
before: status=Open  history_rows=1
after:  status=InProgress  history_rows=2
latest history row: old_status=Open new_status=InProgress

== failing update_ticket_status(ticket 3, 'Cancelled') ==
before: status=Open  history_rows=1
raised: IntegrityError: CHECK constraint failed: status IN ('Open','InProgress','Resolved','Closed')
after:  status=Open  history_rows=1
-> zero trace of the failed attempt: Atomicity holds
```

The successful call changed one `tickets.status` and added one
`ticket_status_history` row, both inside the same transaction. The failing
call (`'Cancelled'` isn't in the `status` CHECK list) changed nothing in
either table; before and after are identical.

## Task 3: concurrency experiment

```bash
python run_concurrency_experiment.py
```

This builds a throwaway `concurrency_experiment.db` (same schema, one
ticket) and runs 5 trials where two threads both do `reopen_count += 1`,
starting at the same time via a `threading.Barrier`, with a small sleep
between the read and the write:

```
Concurrency experiment: 2 threads each do reopen_count += 1
(barrier-synchronized start, 0.1s sleep between read and write; correct final value = 2)

== naive: autocommit read, sleep, write (no transaction) ==
trial 1: final reopen_count = 1
trial 2: final reopen_count = 1
trial 3: final reopen_count = 1
trial 4: final reopen_count = 1
trial 5: final reopen_count = 1

== safe: read + write inside BEGIN IMMEDIATE ... COMMIT ==
trial 1: final reopen_count = 2
trial 2: final reopen_count = 2
trial 3: final reopen_count = 2
trial 4: final reopen_count = 2
trial 5: final reopen_count = 2
```

**Why the safe version works.** This is lock-based concurrency control:
SQLite makes a connection hold the database's write lock before it can
change anything. `BEGIN IMMEDIATE` grabs that write lock right at the start
of the transaction, before the SELECT runs. So when the second thread hits
its own `BEGIN IMMEDIATE`, it has to wait until the first thread's COMMIT
frees the lock, and only then does it read. Its read already sees the first
thread's increment, so it writes `2`. In the naive version each statement
locks and unlocks on its own, so both threads finish their SELECT before
either writes. Both see `0`, both write `1`, and one update is silently
lost.

## Task 4: reports

Each file under `reports/` is a standalone query you can run through any
SQLite client. Below is the raw output of each one against the seeded
database.

### a. `report_tickets_per_employee_inner.sql` (INNER JOIN, 11 rows)

```
emp_id | name | ticket_count
1 | Aarav Sharma | 7
11 | Arjun Reddy | 7
7 | Vivaan Rao | 4
9 | Aditya Menon | 3
6 | Meera Iyer | 2
10 | Sara Khan | 2
2 | Isha Verma | 1
3 | Rohan Gupta | 1
4 | Diya Nair | 1
5 | Kabir Singh | 1
8 | Ananya Joshi | 1
```

Priya Das (`emp_id = 12`) doesn't show up here, which makes sense: she
never raised a ticket, so the inner join drops her.

### b. `report_tickets_per_employee_left.sql` (LEFT JOIN, 12 rows)

```
emp_id | name | joined_rows | ticket_count
1 | Aarav Sharma | 7 | 7
2 | Isha Verma | 1 | 1
3 | Rohan Gupta | 1 | 1
4 | Diya Nair | 1 | 1
5 | Kabir Singh | 1 | 1
6 | Meera Iyer | 2 | 2
7 | Vivaan Rao | 4 | 4
8 | Ananya Joshi | 1 | 1
9 | Aditya Menon | 3 | 3
10 | Sara Khan | 2 | 2
11 | Arjun Reddy | 7 | 7
12 | Priya Das | 1 | 0
```

For Priya Das, `COUNT(*)` is 1 (it counts the NULL-padded joined row) while
`COUNT(t.ticket_id)` is 0, which is her real ticket count.

### c. `report_asset_ticket_coverage.sql` (18 rows + confirmation query)

```
asset_id | asset_tag | ticket_count
1 | AST-001 | 2
2 | AST-002 | 4
3 | AST-003 | 1
4 | AST-004 | 1
5 | AST-005 | 2
6 | AST-006 | 3
7 | AST-007 | 0
8 | AST-008 | 2
9 | AST-009 | 0
10 | AST-010 | 1
11 | AST-011 | 2
12 | AST-012 | 1
13 | AST-013 | 0
14 | AST-014 | 0
15 | AST-015 | 0
16 | AST-016 | 0
17 | AST-017 | 1
18 | AST-018 | 0
```

`AST-018` shows up with `ticket_count = 0`. To double-check it really has
no tickets, the same file also runs a `NOT IN` query listing every asset
that's never appeared on a ticket:

```
asset_id | asset_tag
7 | AST-007
9 | AST-009
13 | AST-013
14 | AST-014
15 | AST-015
16 | AST-016
18 | AST-018
```

### d. `report_employees_above_average.sql` (scalar subquery, 4 rows)

The average tickets per raiser is `30 / 11 ≈ 2.727`, and exactly these four
employees sit above it:

```
emp_id | name | ticket_count
1 | Aarav Sharma | 7
11 | Arjun Reddy | 7
7 | Vivaan Rao | 4
9 | Aditya Menon | 3
```

### e. `report_asset_type_overlap.sql` (UNION then EXCEPT)

`UNION`: assets with at least one incident **or** maintenance ticket,
exactly `{1, 2, 3, 4, 5, 6, 8, 11}`:

```
asset_id
1
2
3
4
5
6
8
11
```

`EXCEPT`: assets with incidents but never maintenance, exactly
`{3, 4, 8, 11}`:

```
asset_id
3
4
8
11
```

### f. `report_type_status_having.sql` (GROUP BY + HAVING, 5 rows)

```
ticket_type | status | ticket_count
incident | Open | 3
service_request | Closed | 4
service_request | InProgress | 3
service_request | Open | 7
service_request | Resolved | 4
```

### g. `report_employee_rank_window.sql` (RANK() window, 11 rows)

```
name | ticket_count | rnk
Aarav Sharma | 7 | 1
Arjun Reddy | 7 | 1
Vivaan Rao | 4 | 3
Aditya Menon | 3 | 4
Meera Iyer | 2 | 5
Sara Khan | 2 | 5
Ananya Joshi | 1 | 7
Diya Nair | 1 | 7
Isha Verma | 1 | 7
Kabir Singh | 1 | 7
Rohan Gupta | 1 | 7
```

Aarav and Arjun tie at rank 1 with 7 tickets each, so `RANK()` (not
`DENSE_RANK()`) skips rank 2 and puts Vivaan at 3.

## Task 5: indexing

Details are in `INDEXING_NOTES.md`. Short version: `EXPLAIN QUERY PLAN` on
report f goes from `SCAN tickets` + `USE TEMP B-TREE FOR GROUP BY` to
`SCAN tickets USING COVERING INDEX idx_tickets_type_status` once the
composite index on `(ticket_type, status)` exists. The index's own sort
order feeds the GROUP BY, so no temp structure is needed.

## Repo layout

```
sentineldesk/
├── README.md
├── engine.py                       # Part 1: domain model + HelpdeskEngine
├── schema.sql                      # Part 2: DDL (3NF)
├── seed_data.sql                   # Part 2: seed data
├── repository.py                   # Part 2: transaction layer + atomicity demo
├── run_concurrency_experiment.py   # Part 2: Task 3
├── reports/                        # Part 2: Task 4, one .sql file per report
│   ├── report_asset_ticket_coverage.sql
│   ├── report_asset_type_overlap.sql
│   ├── report_employee_rank_window.sql
│   ├── report_employees_above_average.sql
│   ├── report_tickets_per_employee_inner.sql
│   ├── report_tickets_per_employee_left.sql
│   └── report_type_status_having.sql
├── INDEXING_NOTES.md               # Part 2: Task 5
└── DESIGN.md                       # Part 3
```
