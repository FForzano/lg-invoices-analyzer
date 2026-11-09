-- Codici ARERA decodificati con le specifiche ufficiali (SII v4.6): a chi vale l'offerta, canali di attivazione,
-- indice di riferimento. Più i filtri preferiti di ogni profilo.
ALTER TABLE offers ADD COLUMN valid_for TEXT;
ALTER TABLE offers ADD COLUMN activation_channels TEXT;
ALTER TABLE offers ADD COLUMN index_name TEXT;

CREATE TABLE filter_presets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id),
    name TEXT NOT NULL,
    query TEXT NOT NULL,
    is_default INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
