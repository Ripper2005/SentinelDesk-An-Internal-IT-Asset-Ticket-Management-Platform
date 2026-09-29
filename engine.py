"""Part 1: ticket domain model + the in-memory helpdesk engine.

This is the business layer of the project. The ticket hierarchy lives here,
along with Employee/Asset (which mirror the DB tables field for field) and
HelpdeskEngine, which loads the Part 2 database into a few dicts/sets so
lookups don't have to hit SQLite every time.
"""

import sqlite3
from abc import ABC, abstractmethod
from datetime import date


class Ticket(ABC):
    """Abstract base class for all tickets.

    Note: you can't do Ticket(ticket_id=1, ...) directly. It raises
    TypeError ("Can't instantiate abstract class Ticket ...") because
    resolution_checklist is abstract and Ticket itself doesn't implement it.
    """

    def __init__(self, ticket_id: int, asset_id, raised_by: int,
                 priority: str, status: str, created_at: str,
                 resolved_at):
        self.ticket_id = ticket_id
        self.asset_id = asset_id          # int or None
        self.raised_by = raised_by
        self.priority = priority
        self.status = status
        self.created_at = created_at
        self.resolved_at = resolved_at    # str or None

    @abstractmethod
    def resolution_checklist(self) -> list[str]:
        """Steps needed before this kind of ticket can be closed."""
        pass

    def age_in_days(self, reference_date: str) -> int:
        # both dates are "YYYY-MM-DD"
        created = date.fromisoformat(self.created_at)
        reference = date.fromisoformat(reference_date)
        return (reference - created).days


class IncidentTicket(Ticket):
    """Something broke: triage, fix, verify."""

    def resolution_checklist(self) -> list[str]:
        return [
            "Triage the incident and confirm impact scope",
            "Find the root cause from logs / diagnostics",
            "Apply or escalate the fix",
            "Verify with the reporter that things work again",
            "Write a short post-incident note for the knowledge base",
        ]


class ServiceRequestTicket(Ticket):
    """Someone needs something: approve it, provision it, confirm it."""

    def resolution_checklist(self) -> list[str]:
        return [
            "Check the request details and who asked for it",
            "Get manager / budget approval",
            "Provision the resource or access",
            "Confirm with the requester that they got it",
        ]


class MaintenanceTicket(Ticket):
    """Planned work: schedule a window, announce it, do it."""

    def resolution_checklist(self) -> list[str]:
        return [
            "Schedule a maintenance window with the asset owners",
            "Announce the downtime to affected users",
            "Take backups / snapshots first",
            "Do the maintenance",
            "Run health checks after and close the window",
        ]


class Employee:
    """Just the employees table as an object."""

    def __init__(self, emp_id, name, department, role):
        self.emp_id = emp_id
        self.name = name
        self.department = department
        self.role = role


class Asset:
    """Just the assets table as an object."""

    def __init__(self, asset_id, asset_tag, category, purchase_date,
                 assigned_to):
        self.asset_id = asset_id
        self.asset_tag = asset_tag
        self.category = category
        self.purchase_date = purchase_date
        self.assigned_to = assigned_to    # emp_id or None


# ticket_type string -> class to build. Ticket itself is never instantiated.
TICKET_CLASSES = {
    "incident": IncidentTicket,
    "service_request": ServiceRequestTicket,
    "maintenance": MaintenanceTicket,
}


class HelpdeskEngine:
    """Loads the SQLite db into in-memory indexes."""

    def __init__(self) -> None:
        self.employees_by_id: dict[int, Employee] = {}
        self.assets_by_id: dict[int, Asset] = {}
        self.tickets_by_status: dict[str, list[Ticket]] = {}
        self.ticket_type_seen: set[str] = set()
        self.count_by_type_status: dict[tuple[str, str], int] = {}

    def load_from_db(self, db_path: str) -> None:
        conn = sqlite3.connect(db_path)

        for row in conn.execute(
                "SELECT emp_id, name, department, role FROM employees"):
            emp = Employee(*row)
            self.employees_by_id[emp.emp_id] = emp

        for row in conn.execute(
                "SELECT asset_id, asset_tag, category, purchase_date,"
                " assigned_to FROM assets"):
            asset = Asset(*row)
            self.assets_by_id[asset.asset_id] = asset

        for row in conn.execute(
                "SELECT ticket_id, asset_id, raised_by, ticket_type,"
                " priority, status, created_at, resolved_at FROM tickets"):
            (ticket_id, asset_id, raised_by, ticket_type,
             priority, status, created_at, resolved_at) = row
            cls = TICKET_CLASSES[ticket_type]
            ticket = cls(ticket_id, asset_id, raised_by, priority, status,
                         created_at, resolved_at)
            self.tickets_by_status.setdefault(status, []).append(ticket)
            self.ticket_type_seen.add(ticket_type)
            key = (ticket_type, status)
            prev = self.count_by_type_status.get(key, 0)
            self.count_by_type_status[key] = prev + 1

        conn.close()


def notify(ticket: Ticket) -> list[str]:
    # This can't fail for any ticket the engine holds: Ticket is an ABC, so
    # Python refuses to even create an object whose class skipped
    # resolution_checklist. If Ticket were a normal duck-typed class instead,
    # an object missing the method would get created fine and only blow up
    # right here with an AttributeError, far away from the real bug.
    return ticket.resolution_checklist()


if __name__ == "__main__":
    engine = HelpdeskEngine()
    engine.load_from_db("sentineldesk.db")

    print("employees:", len(engine.employees_by_id))
    print("assets:", len(engine.assets_by_id))
    for status in ("Open", "InProgress", "Resolved", "Closed"):
        print(f"tickets[{status}]:", len(engine.tickets_by_status[status]))
    print("ticket_type_seen:", sorted(engine.ticket_type_seen))
    print("('service_request','Open'):",
          engine.count_by_type_status[("service_request", "Open")])
    print("('incident','Open'):",
          engine.count_by_type_status[("incident", "Open")])

    # ticket 1 was created 2026-07-02, so age at 2026-07-10 should be 8
    ticket_1 = None
    for tickets in engine.tickets_by_status.values():
        for t in tickets:
            if t.ticket_id == 1:
                ticket_1 = t
    print("ticket 1 age at 2026-07-10:", ticket_1.age_in_days("2026-07-10"))

    # notify() works on each of the three subclasses
    for cls in (IncidentTicket, ServiceRequestTicket, MaintenanceTicket):
        sample = cls(0, None, 1, "Low", "Open", "2026-09-01", None)
        print(f"notify({cls.__name__}): {len(notify(sample))} steps")

    try:
        Ticket(0, None, 1, "Low", "Open", "2026-01-01", None)
    except TypeError as exc:
        print("Ticket() direct instantiation -> TypeError:", exc)
