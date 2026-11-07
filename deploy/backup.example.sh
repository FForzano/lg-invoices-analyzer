#!/usr/bin/env bash
# Backup di database e PDF delle bollette con rclone (Google Drive, S3, NAS remoto, cartella locale...).
# Esempio:  CONTAINER=bollette DATA_DIR=/srv/appdata/bollette/data DEST=gdrive_crypt:bollette ./backup.example.sh
#
# I PDF contengono nome, indirizzo e codice fiscale: usa un remoto cifrato (rclone crypt).
# Il database è copiato con l'API di backup di SQLite, coerente anche se l'app sta scrivendo.
set -euo pipefail

CONTAINER="${CONTAINER:-bollette}"
DATA_DIR="${DATA_DIR:?percorso sull'host della cartella dati (quella montata su /data)}"
DEST="${DEST:?destinazione rclone, es. gdrive_crypt:bollette oppure /mnt/backup/bollette}"
KEEP_DAYS="${KEEP_DAYS:-30}"
LOG="${LOG:-/var/log/backup_bollette.log}"
DATE=$(date +%Y%m%d_%H%M%S)

echo "$(date): backup bollette avviato" | tee -a "$LOG"

# 1) istantanea coerente del database
docker exec "$CONTAINER" python -c \
  "import sqlite3; s=sqlite3.connect('/data/bollette.db'); d=sqlite3.connect('/data/bollette.snapshot.db'); s.backup(d); d.close()"
rclone copyto "$DATA_DIR/bollette.snapshot.db" "$DEST/db/bollette_$DATE.db" --log-file="$LOG"
rm -f "$DATA_DIR/bollette.snapshot.db"

# 2) PDF: sincronizzazione incrementale; i file sostituiti/cancellati finiscono in old/<data>
rclone sync "$DATA_DIR/pdf" "$DEST/pdf" --backup-dir "$DEST/old/$DATE" --log-file="$LOG"

# 3) pulizia
rclone delete "$DEST/db" --min-age "${KEEP_DAYS}d" --log-file="$LOG" || true
rclone delete "$DEST/old" --min-age "${KEEP_DAYS}d" --rmdirs --log-file="$LOG" || true

echo "$(date): backup bollette completato" | tee -a "$LOG"
