# Migrazioni

Due cartelle, una per motore: `sqlite/` e `postgres/`. **Ogni modifica allo schema ha lo stesso numero in entrambe**
(`013_nome.sql` in sqlite e in postgres): un test lo verifica.

- SQLite parte da `001_initial.sql` e tiene la versione in `PRAGMA user_version`.
- PostgreSQL parte da `011_baseline.sql` (lo schema che le migrazioni SQLite 001-011 producono) e tiene la versione
  nella tabella `schema_version`.

Ogni file gira in una transazione: se fallisce, la versione non avanza. Più processi (worker di gunicorn) che partono
insieme sono serializzati (lock su file per SQLite, lock consultivo per PostgreSQL).
Date e orari sono testo ISO (`YYYY-MM-DD HH:MM:SS`, UTC) in entrambi i motori: i confronti restano uguali.
