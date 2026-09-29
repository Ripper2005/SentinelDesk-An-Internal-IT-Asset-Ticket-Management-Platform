-- Task 4f: (ticket_type, status) combinations with at least 3 tickets.
-- Expect 5 rows: ('service_request','Open',7),
-- ('service_request','InProgress',3), ('service_request','Resolved',4),
-- ('incident','Open',3), ('service_request','Closed',4).
SELECT ticket_type,
       status,
       COUNT(*) AS ticket_count
FROM tickets
GROUP BY ticket_type, status
HAVING COUNT(*) >= 3
ORDER BY ticket_type, status;
