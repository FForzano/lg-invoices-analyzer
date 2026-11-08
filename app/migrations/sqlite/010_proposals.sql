-- Proposte ricevute (es. al telefono) da verificare nel contratto prima di accettare. `terms` è il JSON dei
-- campi di Offer: la proposta non è nel catalogo e non entra nei confronti, quindi non serve una colonna per campo.
CREATE TABLE proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id),
    commodity TEXT NOT NULL,
    terms TEXT NOT NULL,
    contact TEXT,
    received_on TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX proposals_profile ON proposals(profile_id);
