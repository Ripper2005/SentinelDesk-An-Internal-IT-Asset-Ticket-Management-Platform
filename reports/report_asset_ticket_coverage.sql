-- Task 4c: ticket coverage per asset, LEFT JOIN. Every asset appears,
-- including AST-018 with 0 tickets.

SELECT a.asset_id,
       a.asset_tag,
       COUNT(t.ticket_id) AS ticket_count
FROM assets a
LEFT JOIN tickets t ON t.asset_id = a.asset_id
GROUP BY a.asset_id, a.asset_tag
ORDER BY a.asset_id;

-- Confirmation query: assets that have never appeared on any ticket.
SELECT asset_id, asset_tag
FROM assets
WHERE asset_id NOT IN (
    SELECT DISTINCT asset_id FROM tickets WHERE asset_id IS NOT NULL
);
