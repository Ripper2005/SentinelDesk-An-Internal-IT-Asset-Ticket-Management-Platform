-- Task 4b: tickets per employee, LEFT JOIN. All 12 employees appear.
-- COUNT(*) counts the NULL-padded row for ticket-less employees (Priya Das
-- -> 1) while COUNT(t.ticket_id) skips NULLs and gives the real count (0).
SELECT e.emp_id,
       e.name,
       COUNT(*) AS joined_rows,
       COUNT(t.ticket_id) AS ticket_count
FROM employees e
LEFT JOIN tickets t ON t.raised_by = e.emp_id
GROUP BY e.emp_id, e.name
ORDER BY e.emp_id;
