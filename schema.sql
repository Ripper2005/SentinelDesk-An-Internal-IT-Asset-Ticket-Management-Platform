-- SentinelDesk schema. It satisfies Third Normal Form (3NF).
-- Every non-key attribute depends on the whole primary key and nothing else:
-- in `employees`, `department` and `role` describe the employee keyed by `emp_id`
-- (not each other), so there is no transitive dependency; in `assets`, `asset_tag`
-- is a unique alternate key but `category`/`purchase_date`/`assigned_to` depend on
-- `asset_id`; in `tickets`, `priority`/`status`/`resolved_at`/`reopen_count` all
-- depend on `ticket_id` alone; and `ticket_status_history` rows depend solely on
-- `history_id`. No non-key column in any table determines another non-key column.

CREATE TABLE employees (
    emp_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    role TEXT NOT NULL
);

CREATE TABLE assets (
    asset_id INTEGER PRIMARY KEY,
    asset_tag TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    purchase_date TEXT NOT NULL,
    assigned_to INTEGER REFERENCES employees(emp_id)
);

CREATE TABLE tickets (
    ticket_id INTEGER PRIMARY KEY,
    asset_id INTEGER REFERENCES assets(asset_id),
    raised_by INTEGER NOT NULL REFERENCES employees(emp_id),
    ticket_type TEXT NOT NULL CHECK (ticket_type IN ('incident','service_request','maintenance')),
    priority TEXT NOT NULL CHECK (priority IN ('Low','Medium','High','Critical')),
    status TEXT NOT NULL CHECK (status IN ('Open','InProgress','Resolved','Closed')),
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    reopen_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE ticket_status_history (
    history_id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES tickets(ticket_id),
    old_status TEXT,
    new_status TEXT NOT NULL,
    changed_at TEXT NOT NULL
);
