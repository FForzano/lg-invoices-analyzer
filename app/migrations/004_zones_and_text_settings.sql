ALTER TABLE offers ADD COLUMN zones TEXT;

-- le impostazioni ora possono contenere anche testo (codici ISTAT): colonna senza tipo
CREATE TABLE settings_new (key TEXT PRIMARY KEY, value);
INSERT INTO settings_new SELECT key, value FROM settings;
DROP TABLE settings;
ALTER TABLE settings_new RENAME TO settings;
