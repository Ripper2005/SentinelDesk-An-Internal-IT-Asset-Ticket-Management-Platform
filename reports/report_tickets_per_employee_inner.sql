-- Task 4a: tickets per employee, INNER JOIN (employees with zero tickets
-- are excluded, so Priya Das does not appear). Expect 11 rows.
SELECT e.emp_id,
       e.name,
       COUNT(t.ticket_id) AS ticket_count
FROM employees e
INNER JOIN tickets t ON t.raised_by = e.emp_id
GROUP BY e.emp_id, e.name
ORDER BY ticket_count DESC, e.emp_id;
