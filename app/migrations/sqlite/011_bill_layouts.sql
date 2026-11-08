-- Layout di lettura insegnati dall'utente: `rules` è il JSON delle regole etichetta → valore
-- (services/layouts.py). Globali, perché descrivono il modello di bolletta di un fornitore.
CREATE TABLE bill_layouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    signature TEXT NOT NULL,
    rules TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
