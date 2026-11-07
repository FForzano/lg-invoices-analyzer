-- Profili: più appartamenti nella stessa installazione. Bollette e offerta attuale appartengono a un profilo;
-- le offerte importate o inserite a mano senza profilo (profile_id NULL) sono il catalogo condiviso.
CREATE TABLE profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    region TEXT NOT NULL DEFAULT '',
    province TEXT NOT NULL DEFAULT '',
    comune TEXT NOT NULL DEFAULT '',
    default_power_kw REAL NOT NULL DEFAULT 3.0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- il primo profilo eredita località e potenza che erano nelle impostazioni
INSERT INTO profiles (id, name, region, province, comune, default_power_kw)
SELECT 1, 'Casa',
    COALESCE((SELECT value FROM settings WHERE key = 'region'), '08'),
    COALESCE((SELECT value FROM settings WHERE key = 'province'), '038'),
    COALESCE((SELECT value FROM settings WHERE key = 'comune'), '038008'),
    CAST(COALESCE((SELECT value FROM settings WHERE key = 'default_power_kw'), 3.0) AS REAL);
DELETE FROM settings WHERE key IN ('region', 'province', 'comune', 'default_power_kw');

ALTER TABLE bills ADD COLUMN profile_id INTEGER REFERENCES profiles(id);
UPDATE bills SET profile_id = 1;
ALTER TABLE offers ADD COLUMN profile_id INTEGER REFERENCES profiles(id);
UPDATE offers SET profile_id = 1 WHERE is_current = 1;
CREATE INDEX bills_profile ON bills(profile_id);
