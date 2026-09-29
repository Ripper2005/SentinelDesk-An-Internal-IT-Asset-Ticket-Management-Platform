-- Task 4d: employees whose ticket count exceeds the average tickets per
-- raiser (scalar subquery: total tickets / distinct raisers = 30/11
-- ~ 2.727). Expect exactly 4 employees: Aarav Sharma (7), Arjun Reddy (7),
-- Vivaan Rao (4), Aditya Menon (3).
SELECT e.emp_id,
       e.name,
       COUNT(t.ticket_id) AS ticket_count
FROM employees e
INNER JOIN tickets t ON t.raised_by = e.emp_id
GROUP BY e.emp_id, e.name
HAVING COUNT(t.ticket_id) > (
    SELECT CAST(COUNT(*) AS REAL) / COUNT(DISTINCT raised_by)
    FROM tickets
)
ORDER BY ticket_count DESC, e.name;
