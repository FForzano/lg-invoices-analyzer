#!/usr/bin/env bash
# Aggiorna le offerte dal Portale Offerte (open data ARERA/Acquirente Unico) e i prezzi storici di PUN/PSV.
# Equivale al pulsante «Aggiorna dal Portale Offerte». Pianificalo una volta a settimana.
# Serve accesso a internet dal container. Non adotta i prezzi recenti: quello lo scegli tu in Impostazioni.
set -euo pipefail

URL="${URL:-http://localhost:8090}"
# Con il login attivo imposta CRON_TOKEN (stesso valore del container): vale solo per questa operazione.
AUTH=()
[ -n "${CRON_TOKEN:-}" ] && AUTH=(-H "Authorization: Bearer $CRON_TOKEN")
curl -fsS --max-time 300 -X POST ${AUTH[@]+"${AUTH[@]}"} "$URL/api/offers/import-arera" -o /dev/null
echo "$(date): offerte aggiornate"
