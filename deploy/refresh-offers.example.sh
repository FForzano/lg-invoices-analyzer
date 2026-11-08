#!/usr/bin/env bash
# Aggiorna le offerte dal Portale Offerte (open data ARERA/Acquirente Unico) e i prezzi storici di PUN/PSV.
# Equivale al pulsante «Aggiorna dal Portale Offerte». Pianificalo una volta a settimana.
# Serve accesso a internet dal container. Non adotta i prezzi recenti: quello lo scegli tu in Impostazioni.
set -euo pipefail

URL="${URL:-http://localhost:8090}"
curl -fsS --max-time 300 -X POST "$URL/api/offers/import-arera" -o /dev/null
echo "$(date): offerte aggiornate"
