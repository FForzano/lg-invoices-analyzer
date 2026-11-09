-- Recupero password via email (solo se è configurato un server di posta, vedi MAIL_HOST): nel database sta solo l'impronta
-- del token; vale un'ora e una volta sola. Un nuovo link per lo stesso utente annulla i precedenti.
CREATE TABLE password_resets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL
);
CREATE INDEX password_resets_user ON password_resets(user_id);
