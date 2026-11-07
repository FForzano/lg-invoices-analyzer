CREATE TABLE IF NOT EXISTS bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    commodity TEXT NOT NULL CHECK (commodity IN ('power', 'gas')),
    supplier TEXT,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    consumption REAL,
    kwh_f1 REAL, kwh_f2 REAL, kwh_f3 REAL,
    mc REAL, coeff_c REAL,
    power_kw REAL,
    reading_type TEXT CHECK (reading_type IN ('effettiva', 'stimata')),
    total_eur REAL,
    annual_consumption REAL,
    annual_f1 REAL, annual_f2 REAL, annual_f3 REAL,
    annual_spend REAL,
    pdf_path TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    commodity TEXT NOT NULL CHECK (commodity IN ('power', 'gas')),
    supplier TEXT NOT NULL,
    name TEXT NOT NULL,
    price_type TEXT NOT NULL CHECK (price_type IN ('fixed', 'indexed')),
    price REAL,
    price_f1 REAL, price_f2 REAL, price_f3 REAL,
    avg_price REAL,
    spread REAL,
    fixed_fee_month REAL,
    power_fee_kw_month REAL,
    one_off_discount REAL,
    expires_on TEXT,
    is_current INTEGER NOT NULL DEFAULT 0,
    source TEXT,
    loss_pct REAL,
    dispatching REAL,
    capacity REAL,
    gas_mgmt REAL,
    pcs_adjustment REAL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value REAL NOT NULL
);
