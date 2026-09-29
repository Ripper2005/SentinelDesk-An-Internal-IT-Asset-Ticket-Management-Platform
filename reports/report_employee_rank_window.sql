-- Task 4g: rank raisers by ticket count using a window function.
-- RANK() (not DENSE_RANK()) must skip to 3 after the two-way rank-1 tie
-- (Aarav Sharma and Arjun Reddy, 7 tickets each). Vivaan Rao ranks 3.
SELECT name,
       ticket_count,
       RANK() OVER (ORDER BY ticket_count DESC) AS rnk
FROM (
    SELECT e.emp_id,
           e.name,
           COUNT(t.ticket_id) AS ticket_count
    FROM employees e
    INNER JOIN tickets t ON t.raised_by = e.emp_id
    GROUP BY e.emp_id, e.name
)
ORDER BY rnk, name;
