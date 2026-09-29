-- Task 4e: set operations over "assets with >=1 incident ticket" and
-- "assets with >=1 maintenance ticket".

-- (i) UNION: assets touched by either type. Expect {1,2,3,4,5,6,8,11}.
SELECT DISTINCT asset_id FROM tickets
WHERE ticket_type = 'incident' AND asset_id IS NOT NULL
UNION
SELECT DISTINCT asset_id FROM tickets
WHERE ticket_type = 'maintenance' AND asset_id IS NOT NULL
ORDER BY asset_id;

-- (ii) EXCEPT: incident assets never touched by maintenance.
-- Expect {3,4,8,11}.
SELECT DISTINCT asset_id FROM tickets
WHERE ticket_type = 'incident' AND asset_id IS NOT NULL
EXCEPT
SELECT DISTINCT asset_id FROM tickets
WHERE ticket_type = 'maintenance' AND asset_id IS NOT NULL
ORDER BY asset_id;
