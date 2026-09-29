"""Part 2 Task 3: the concurrency experiment, run for real.

Two threads both read reopen_count for the same ticket, sleep a bit, then
write back reopen_count + 1. Both increments should land, so the correct
final value is 2.

- reopen_ticket_naive: plain autocommit, no transaction around the
  read+write. Both threads can read the same pre-increment value, so one
  update gets lost (final value 1).
- reopen_ticket_safe: read+write wrapped in BEGIN IMMEDIATE. The second
  thread has to wait on SQLite's write lock until the first commits, so the
  two increments happen one after the other (final value 2).

It runs against a throwaway db, not the seeded one.
"""

import os
import sqlite3
import threading
import time

EXPERIMENT_DB = "concurrency_experiment.db"
TICKET_ID = 1
WORKERS = 2
TRIALS = 5
SLEEP_SECONDS = 0.1


def reopen_ticket_naive(conn, ticket_id):
    count = conn.execute(
        "SELECT reopen_count FROM tickets WHERE ticket_id = ?", (ticket_id,)
    ).fetchone()[0]
    time.sleep(SLEEP_SECONDS)  # give the other thread time to read too
    conn.execute(
        "UPDATE tickets SET reopen_count = ? WHERE ticket_id = ?",
        (count + 1, ticket_id),
    )


def reopen_ticket_safe(conn, ticket_id):
    conn.execute("BEGIN IMMEDIATE")
    try:
        count = conn.execute(
            "SELECT reopen_count FROM tickets WHERE ticket_id = ?",
            (ticket_id,),
        ).fetchone()[0]
        time.sleep(SLEEP_SECONDS)
        conn.execute(
            "UPDATE tickets SET reopen_count = ? WHERE ticket_id = ?",
            (count + 1, ticket_id),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def worker(db_path, barrier, fn):
    # sqlite connections aren't shareable across threads, so each thread
    # opens its own. isolation_level=None means real autocommit mode, and
    # timeout=10 lets a blocked BEGIN IMMEDIATE wait for the other txn.
    conn = sqlite3.connect(db_path, isolation_level=None, timeout=10)
    try:
        barrier.wait()  # both threads start together
        fn(conn, TICKET_ID)
    finally:
        conn.close()


def build_experiment_db():
    """Throwaway db: real schema, one employee, one ticket at reopen_count 0."""
    if os.path.exists(EXPERIMENT_DB):
        os.remove(EXPERIMENT_DB)
    conn = sqlite3.connect(EXPERIMENT_DB)
    conn.executescript(open("schema.sql", encoding="utf-8").read())
    conn.execute(
        "INSERT INTO employees (emp_id, name, department, role)"
        " VALUES (1, 'Experiment User', 'IT Support', 'Support Technician')"
    )
    conn.execute(
        "INSERT INTO tickets"
        " (ticket_id, asset_id, raised_by, ticket_type, priority,"
        "  status, created_at, resolved_at, reopen_count)"
        " VALUES (1, NULL, 1, 'incident', 'High', 'Open',"
        "         '2026-09-01', NULL, 0)"
    )
    conn.commit()
    conn.close()


def reset_reopen_count():
    conn = sqlite3.connect(EXPERIMENT_DB)
    conn.execute(
        "UPDATE tickets SET reopen_count = 0 WHERE ticket_id = ?", (TICKET_ID,)
    )
    conn.commit()
    conn.close()


def read_reopen_count():
    conn = sqlite3.connect(EXPERIMENT_DB)
    value = conn.execute(
        "SELECT reopen_count FROM tickets WHERE ticket_id = ?", (TICKET_ID,)
    ).fetchone()[0]
    conn.close()
    return value


def run_trial(fn):
    reset_reopen_count()
    barrier = threading.Barrier(WORKERS)
    threads = [
        threading.Thread(target=worker, args=(EXPERIMENT_DB, barrier, fn))
        for _ in range(WORKERS)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return read_reopen_count()


def main():
    build_experiment_db()

    print("Concurrency experiment: 2 threads each do reopen_count += 1")
    print(f"(barrier-synchronized start, {SLEEP_SECONDS}s sleep between "
          f"read and write; correct final value = {WORKERS})\n")

    print("== naive: autocommit read, sleep, write (no transaction) ==")
    for trial in range(1, TRIALS + 1):
        final = run_trial(reopen_ticket_naive)
        print(f"trial {trial}: final reopen_count = {final}")

    print("\n== safe: read + write inside BEGIN IMMEDIATE ... COMMIT ==")
    for trial in range(1, TRIALS + 1):
        final = run_trial(reopen_ticket_safe)
        print(f"trial {trial}: final reopen_count = {final}")


if __name__ == "__main__":
    main()
