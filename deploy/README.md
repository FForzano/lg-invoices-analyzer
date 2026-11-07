# Installare l'app su un NAS o home server

Guida e template per metterla in produzione in casa (OpenMediaVault, Synology, Unraid, Raspberry, un qualsiasi host con Docker).
L'app è pensata per la **rete locale**: non ha autenticazione.

| File | A cosa serve |
|---|---|
| `docker-compose.example.yml` | Servizio Docker con volume dati, utente non-root, healthcheck |
| `example.env` | Variabili da copiare in `.env` |
| `backup.example.sh` | Backup di database (istantanea coerente) e PDF con rclone |
| `refresh-offers.example.sh` | Aggiornamento settimanale di offerte e prezzi storici |
| `Caddyfile.example` | Reverse proxy con login, se vuoi raggiungerla da fuori casa |

## Avvio rapido

```bash
mkdir bollette && cd bollette
curl -O https://raw.githubusercontent.com/FForzano/lg-invoices-analyzer/main/deploy/docker-compose.example.yml
curl -o .env https://raw.githubusercontent.com/FForzano/lg-invoices-analyzer/main/deploy/example.env
mv docker-compose.example.yml docker-compose.yml

# 1. imposta SECRET_KEY e, se serve, DATA_PATH / PUID / PGID / PORT
sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$(openssl rand -hex 32)/" .env

# 2. la cartella dati deve essere scrivibile dall'utente del container
mkdir -p data && sudo chown 1000:100 data

# 3. avvio (il primo build scarica le dipendenze: qualche minuto)
docker compose up -d --build
```

Apri `http://<ip-del-nas>:8090`. Al primo avvio il database viene creato e migrato da solo.

## Permessi della cartella dati

Il processo gira come `PUID:PGID` (default `1000:100`) e deve poter scrivere in `DATA_PATH`. Se non può, il container
si ferma con *«Cartella dati non scrivibile»*: dai la proprietà della cartella a quell'utente (`chown`) oppure
imposta `PUID`/`PGID` su quelli del tuo utente (`id`). Sul tuo host i valori giusti sono spesso quelli che usano già gli altri
container (linuxserver.io: stessi `PUID`/`PGID`).

## Primo utilizzo

1. *Offerte → Aggiorna dal Portale Offerte*: importa oltre 3.000 offerte domestiche (serve internet).
2. *Bollette → Carica*: il PDF viene letto in locale; l'offerta attuale e i parametri PUN/PSV si ricavano dalla bolletta.
3. La home dice se conviene cambiare.

In *Impostazioni* c'è la **località** (codici ISTAT: regione, provincia, comune): filtra le offerte valide solo in certe aree.
Il default è Ferrara; cambiala.

## Sicurezza e privacy

- **Nessun login.** Non esporre la porta su internet. Per usarla fuori casa: VPN (WireGuard, Tailscale) oppure un reverse
  proxy con autenticazione (`Caddyfile.example`).
- **Dati personali.** Le bollette contengono nome, indirizzo, codice fiscale. Restano nella cartella dati.
  L'unica uscita verso l'esterno è l'aggiornamento delle offerte (scarica file pubblici, non invia nulla)
  e, solo se imposti `ANTHROPIC_API_KEY` e la lettura locale non basta, il testo di quella bolletta verso l'API Anthropic.
  Per non inviare mai nulla, non impostare la chiave.
- Usa un `SECRET_KEY` casuale e non committare `.env`.

## Aggiornare l'app

```bash
# backup (vedi sotto), poi:
docker compose up -d --build --pull
```

Le migrazioni del database partono da sole all'avvio. Se hai usato `build:` da URL git, `--build` riscarica l'ultima versione.

## Backup

`backup.example.sh` copia il database con l'API di backup di SQLite (coerente anche con l'app in uso) e sincronizza i PDF,
tenendo le versioni sostituite per `KEEP_DAYS` giorni. Usa **rclone**, quindi va bene per Google Drive, S3, SFTP o una cartella locale.
Dato che i PDF sono sensibili, usa un remoto cifrato (`rclone crypt`).

```bash
CONTAINER=bollette DATA_DIR=/percorso/data DEST=gdrive_crypt:bollette ./backup.example.sh
```

Ripristino: ferma il container, rimetti `bollette_<data>.db` come `DATA_DIR/bollette.db` e i PDF in `DATA_DIR/pdf`, riavvia.

## Pianificare gli aggiornamenti

Su **OpenMediaVault**: *Sistema → Attività pianificate → Aggiungi*, utente `root`, comando
`/percorso/refresh-offers.sh`, una volta a settimana (idem per il backup).
Con **cron**: `0 4 * * 1  /percorso/refresh-offers.sh`.
Con **systemd**: un timer `OnCalendar=weekly` che avvia lo script.

L'aggiornamento carica anche i prezzi storici di PUN/PSV, ma non cambia le ipotesi: adotti i prezzi recenti da *Impostazioni*.

## Senza Docker

```bash
git clone https://github.com/FForzano/lg-invoices-analyzer.git && cd lg-invoices-analyzer
uv sync --no-dev
DATA_DIR=$PWD/data SECRET_KEY=$(openssl rand -hex 32) uv run gunicorn -b 0.0.0.0:8080 --workers 2 --timeout 180 "app:create_app()"
```

## Problemi frequenti

| Sintomo | Causa / soluzione |
|---|---|
| Container che si riavvia, log «Cartella dati non scrivibile» | Permessi di `DATA_PATH`: vedi sopra |
| `port is already allocated` | Cambia `PORT` nel `.env` |
| Stato `unhealthy` | `docker logs bollette`; di solito è uno dei due punti precedenti |
| «Download non riuscito» nell'aggiornamento offerte | Il container non raggiunge `www.ilportaleofferte.it` (DNS/firewall) |
| Il verdetto sembra troppo ottimistico | Controlla località e condizioni sul sito del venditore: l'XML non dichiara tutte le restrizioni |
