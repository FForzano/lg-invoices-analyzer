# Installare l'app su un NAS o home server

Guida e template per metterla in produzione in casa (OpenMediaVault, Synology, Unraid, Raspberry, un qualsiasi host con Docker).
L'app è pensata per la **rete locale**; il login è opzionale (vedi «Configurazione opzionale»).

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

# 1. se serve, imposta DATA_PATH / PUID / PGID / PORT nel .env

# 2. la cartella dati deve essere scrivibile dall'utente del container
mkdir -p data && sudo chown 1000:100 data

# 3. avvio (scarica l'immagine pubblicata dalla CI)
docker compose up -d
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

- **Login spento di default.** Senza `AUTH_ENABLED=true` non esporre la porta su internet. Per usarla fuori casa: VPN (WireGuard, Tailscale)
  oppure un reverse proxy con HTTPS (`Caddyfile.example`); con il login attivo scegli una `ADMIN_PASSWORD` robusta.
- **Dati personali.** Le bollette contengono nome, indirizzo, codice fiscale. Restano nella cartella dati.
  L'unica uscita verso l'esterno è l'aggiornamento delle offerte (scarica file pubblici, non invia nulla)
  e, solo se imposti `ANTHROPIC_API_KEY` e la lettura locale non basta, il testo di quella bolletta verso l'API Anthropic.
  Per non inviare mai nulla, non impostare la chiave.
- Non committare `.env`: contiene password e chiavi.

## Configurazione opzionale

**Di default non cambia nulla**: SQLite e PDF nella cartella dati, nessun login. Ogni funzione si accende con variabili
d'ambiente (nel `.env`); si possono usare separatamente.

| Funzione | Variabili |
|---|---|
| **Login** | `AUTH_ENABLED=true`. Al primo avvio nasce un amministratore: `ADMIN_EMAIL` (default `admin@bollette.local`) e `ADMIN_PASSWORD` (se non la imposti è `admin` e al primo accesso viene chiesto di cambiarla). Da *Utenti* l'amministratore crea gli altri account; ognuno ha i **suoi profili** (quante case vuole) e cambia nome, email e password da *Account*. I profili già esistenti passano all'amministratore. Il **catalogo offerte** e le ipotesi su **PUN/PSV** (e perdite/dispacciamento) li gestiscono solo gli amministratori e il cron; gli altri utenti inseriscono la propria offerta attuale. Dettagli di sicurezza sotto. |
| **PostgreSQL** | `DATABASE_URL=postgresql://utente:password@host:5432/bollette` (database già creato; le tabelle le crea l'app). Senza: `sqlite:///` nella cartella dati. |
| **PDF su S3 / MinIO / R2** | `STORAGE_DRIVER=s3`, `S3_BUCKET`, `S3_ENDPOINT_URL` (vuoto per AWS), `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` (senza: catena standard di AWS, es. ruolo IAM), `S3_PREFIX` (cartella nel bucket), `S3_ADDRESSING=path\|virtual` (con un endpoint è «path», come vuole MinIO). Senza: `STORAGE_PATH`, default `DATA_DIR/pdf`. |

**Aggiornamento offerte con il login attivo.** Il cron non ha un account. Il modo più semplice è il comando, che non passa dal web
e quindi non ha token da custodire:

```bash
docker exec bollette flask --app app import-offers      # es. una volta a settimana, da cron dell'host
```

In alternativa, via HTTP (`deploy/refresh-offers.example.sh`): imposta `CRON_TOKEN` nel container e nello script; il token vale solo per quell'operazione.

**Come funziona l'accesso.** Password con **Argon2id**. Dopo l'accesso il browser riceve due cookie `HttpOnly` + `SameSite=Strict`
(+ `Secure` in HTTPS): un **access token JWT** da 15 minuti e un **refresh token** che cambia a ogni rinnovo (*rotation*). Se un refresh
token già usato ricompare, qualcuno l'ha copiato: l'intero accesso viene revocato. JavaScript non legge i cookie, quindi un XSS non li ruba;
le richieste che modificano dati richiedono un header che un altro sito non può aggiungere (anti-CSRF). Cambiare o reimpostare la password
scollega subito gli altri dispositivi. La chiave dei JWT (`SECRET_KEY`) se manca viene generata e conservata nel database.
Dopo 5 password errate l'account si blocca per 15 minuti. Metti comunque l'app dietro **HTTPS** se la raggiungi fuori casa.


**Passare a PostgreSQL o S3 con dati già presenti** (una volta, con la nuova configurazione nel `.env`):

```bash
docker compose exec bollette flask --app app import-sqlite /data/bollette.db   # copia i dati nel nuovo database (che deve essere vuoto)
docker compose exec bollette flask --app app upload-pdfs                       # carica nello storage S3 i PDF che stanno in /data/pdf
```

Il backup di `deploy/backup.example.sh` copia il database SQLite: con PostgreSQL usa `pg_dump`, con S3 le copie del bucket.
Dopo lo spostamento puoi togliere i vecchi `bollette.db` e `pdf/`.

## Aggiornare l'app

```bash
# backup (vedi sotto), poi:
docker compose pull && docker compose up -d
```

Le migrazioni del database partono da sole all'avvio. Se costruisci l'immagine da URL git (`build:`), usa invece `docker compose up -d --build`.

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
DATA_DIR=$PWD/data uv run gunicorn -b 0.0.0.0:8080 --workers 2 --timeout 180 "app:create_app()"
```

## Problemi frequenti

| Sintomo | Causa / soluzione |
|---|---|
| Container che si riavvia, log «Cartella dati non scrivibile» | Permessi di `DATA_PATH`: vedi sopra |
| `port is already allocated` | Cambia `PORT` nel `.env` |
| Stato `unhealthy` | `docker logs bollette`; di solito è uno dei due punti precedenti |
| «Download non riuscito» nell'aggiornamento offerte | Il container non raggiunge `www.ilportaleofferte.it` (DNS/firewall) |
| Il verdetto sembra troppo ottimistico | Controlla località e condizioni sul sito del venditore: l'XML non dichiara tutte le restrizioni |
