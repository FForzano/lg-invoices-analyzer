-- Sessioni con access token breve (JWT) e refresh token a rotazione:
--   family_id  = un accesso (un dispositivo); i refresh della stessa famiglia si susseguono
--   used_at    = quando quel refresh è stato scambiato per uno nuovo; se ricompare dopo, è stato rubato e l'intera famiglia cade
--   token_version = si incrementa al cambio/reimpostazione della password e invalida subito tutti gli access token
-- Le sessioni del vecchio schema (token opachi) non valgono più: si accede di nuovo.
DELETE FROM sessions;
ALTER TABLE sessions ADD COLUMN family_id TEXT;
ALTER TABLE sessions ADD COLUMN used_at TEXT;
CREATE INDEX sessions_family ON sessions(family_id);
ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0;

-- chiave di firma dei JWT, generata al primo avvio se non c'è SECRET_KEY (così funziona anche con più istanze sullo stesso database)
CREATE TABLE auth_secrets (
    name TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
