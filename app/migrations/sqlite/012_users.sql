-- Account (login opzionale, AUTH_ENABLED) e sessioni. Con il login spento queste tabelle restano vuote.
-- I profili esistenti restano senza proprietario (user_id NULL): al primo avvio con il login attivo
-- passano all'amministratore creato di default.
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    must_change_password INTEGER NOT NULL DEFAULT 0,
    failed_logins INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- del token si conserva solo l'impronta (SHA-256): un database trapelato non permette di entrare
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_hash TEXT NOT NULL UNIQUE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT NOT NULL
);
CREATE INDEX sessions_user ON sessions(user_id);

ALTER TABLE profiles ADD COLUMN user_id INTEGER REFERENCES users(id);
CREATE INDEX profiles_user ON profiles(user_id);
