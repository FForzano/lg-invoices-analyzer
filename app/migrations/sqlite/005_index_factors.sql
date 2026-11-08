-- stagionalità mensile di PUN/PSV (media 1.0), calcolata dai prezzi storici del Portale Offerte
CREATE TABLE IF NOT EXISTS index_factors (
    index_name TEXT NOT NULL CHECK (index_name IN ('pun', 'psv')),
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    factor REAL NOT NULL,
    PRIMARY KEY (index_name, month)
);
