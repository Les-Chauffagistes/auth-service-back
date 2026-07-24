-- Staging incident (2026-07-24): the `id` sequences on these tables had fallen behind
-- the actual max id in each table (data was loaded with explicit ids without advancing
-- the sequence), so every `INSERT ... DEFAULT id` collided with an existing row until
-- the sequence caught up on its own. Resync each sequence to the table's current data.
SELECT setval(pg_get_serial_sequence('"users"', 'id'), COALESCE((SELECT MAX(id) FROM "users"), 1));
SELECT setval(pg_get_serial_sequence('"ln_users"', 'id'), COALESCE((SELECT MAX(id) FROM "ln_users"), 1));
SELECT setval(pg_get_serial_sequence('"password_users"', 'id'), COALESCE((SELECT MAX(id) FROM "password_users"), 1));
SELECT setval(pg_get_serial_sequence('"refresh_tokens"', 'id'), COALESCE((SELECT MAX(id) FROM "refresh_tokens"), 1));
