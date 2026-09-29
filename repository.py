"""Part 2: Repository / transaction layer (the data-access layer).

Any write that touches more than one row goes through an explicit
BEGIN ... COMMIT here, with ROLLBACK if anything throws, so tickets and
ticket_status_history can never end up out of sync.
"""

import os
import shutil
import sqlite3
from datetime import date


class Repository:
    """Every write goes through this class; no loose SQL elsewhere."""

    def update_ticket_status(self, conn, ticket_id: int,
                             new_status: str) -> None:
        """Update the ticket's status and log it in ticket_status_history.

        Both statements are in one transaction, so if the UPDATE fails (say
        new_status isn't allowed by the CHECK constraint) or the INSERT
        fails, ROLLBACK wipes the whole thing, not just half of it.
        """
        row = conn.execute(
            "SELECT status FROM tickets WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"no ticket with ticket_id={ticket_id}")
        old_status = row[0]

        conn.execute("BEGIN")
        try:
            conn.execute(
                "UPDATE tickets SET status = ? WHERE ticket_id = ?",
                (new_status, ticket_id),
            )
            conn.execute(
                "INSERT INTO ticket_status_history"
                " (ticket_id, old_status, new_status, changed_at)"
                " VALUES (?, ?, ?, ?)",
                (ticket_id, old_status, new_status, date.today().isoformat()),
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    def raise_ticket(self, conn, ticket_id: int, asset_id, raised_by: int,
                     ticket_type: str, priority: str, created_at: str) -> None:
        """Insert a ticket plus its 'created' history row, atomically."""
        conn.execute("BEGIN")
        try:
            conn.execute(
                "INSERT INTO tickets"
                " (ticket_id, asset_id, raised_by, ticket_type, priority,"
                "  status, created_at, resolved_at)"
                " VALUES (?, ?, ?, ?, ?, 'Open', ?, NULL)",
                (ticket_id, asset_id, raised_by, ticket_type, priority,
                 created_at),
            )
            conn.execute(
                "INSERT INTO ticket_status_history"
                " (ticket_id, old_status, new_status, changed_at)"
                " VALUES (?, NULL, 'Open', ?)",
                (ticket_id, created_at),
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise


def get_status(conn, ticket_id):
    return conn.execute(
        "SELECT status FROM tickets WHERE ticket_id = ?", (ticket_id,)
    ).fetchone()[0]


def count_history_rows(conn, ticket_id):
    return conn.execute(
        "SELECT COUNT(*) FROM ticket_status_history WHERE ticket_id = ?",
        (ticket_id,),
    ).fetchone()[0]


def demo_atomicity():
    """Show before/after so we can see the failed call left nothing behind.

    Works on a copy of the seeded db so the real sentineldesk.db doesn't
    get touched.
    """
    repo = Repository()
    work_db = "demo_atomicity.db"
    shutil.copyfile("sentineldesk.db", work_db)

    # a call that works: one status update + one history row
    conn = sqlite3.connect(work_db)
    print("== successful update_ticket_status(ticket 2, 'InProgress') ==")
    print(f"before: status={get_status(conn, 2)}  "
          f"history_rows={count_history_rows(conn, 2)}")
    repo.update_ticket_status(conn, 2, "InProgress")
    print(f"after:  status={get_status(conn, 2)}  "
          f"history_rows={count_history_rows(conn, 2)}")

    latest = conn.execute(
        "SELECT old_status, new_status FROM ticket_status_history"
        " WHERE ticket_id = 2 ORDER BY history_id DESC LIMIT 1"
    ).fetchone()
    print(f"latest history row: old_status={latest[0]} new_status={latest[1]}")
    conn.close()

    # a call that's meant to fail: 'Cancelled' isn't in the status CHECK
    conn = sqlite3.connect(work_db)
    print("\n== failing update_ticket_status(ticket 3, 'Cancelled') ==")
    print(f"before: status={get_status(conn, 3)}  "
          f"history_rows={count_history_rows(conn, 3)}")
    try:
        repo.update_ticket_status(conn, 3, "Cancelled")
    except sqlite3.IntegrityError as exc:
        print(f"raised: IntegrityError: {exc}")
    print(f"after:  status={get_status(conn, 3)}  "
          f"history_rows={count_history_rows(conn, 3)}")
    print("-> zero trace of the failed attempt: Atomicity holds")
    conn.close()

    os.remove(work_db)


if __name__ == "__main__":
    demo_atomicity()
