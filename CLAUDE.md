# Bollette self-hosted — confronto offerte luce/gas

## Project Context for Claude Code

App Flask + SQLite, un solo container, uso domestico in rete locale. Cosa fa e come si usa: `README.md`; installazione su NAS/home server e template (compose, backup, cron, proxy): `deploy/`. Le specifiche originali non sono nel repo pubblico.

## Commands

```bash
uv run pytest                                    # tutti i test
uv run flask --app "app:create_app()" run --debug
docker compose up --build
```

I template per la produzione sono in `deploy/` (non committare `.env`).

## Architecture

Entry point `app/__init__.py` (`create_app`, config da env: `DATA_DIR`, `SECRET_KEY`, `ANTHROPIC_*`).

- `app/models.py` — dataclass `Bill` e `Offer`. **Sono la fonte di verità** per colonne, parsing form/CSV e schema del tool LLM.
- `app/forms.py` — `parse(cls, mapping)`: stringhe → dataclass, guidato dai type hint (virgola decimale, `choices` nei metadata dei campi).
- `app/db.py` — connessione SQLite e repository (`list_*`, `add_bill`, `save_offer`, `get_settings`…). SQL grezzo, nessun ORM.
- `app/migrations/` — migrazioni SQL numerate (`NNN_nome.sql`), applicate all'avvio da `migrations.migrate` (versione in `PRAGMA user_version`).
- `app/services/` — logica di dominio **pura, senza Flask**: `pricing` (stima/confronto), `consumption` (consumo annuo), `history`, `alerts`, `offers_csv`, `bill_parser` (lettura PDF a regole + condizioni dell'offerta attuale), `seasonality` (profili di consumo, fattori mensili PUN/PSV), `verdict` (conviene cambiare? risparmio e sensibilità PUN/PSV), `extraction` (orchestra regole → LLM come ripiego), `arera` (import open data Portale Offerte), `power` (consiglio sulla potenza impegnata dai picchi in bolletta), `paging` (paginazione delle liste: bollette, offerte, confronto; macro `pager` in `_macros.html`).
- `app/analysis.py` — `analyze(commodity)`: unisce database e servizi (consumo, confronto, verdetto); usata da home e confronto.
- Proposte (`/proposal`, `routes/proposal.py`): form per valutare un'offerta non pubblicata (es. telefonata); `analysis.evaluate_proposal` → `verdict.judge_proposal` contro l'offerta attuale. Valutare non salva nulla; «Salva» scrive in `proposals` (migrazione 010, per profilo, `terms` = JSON dei campi di `Offer` via `services/proposal.py`, nessuna colonna per campo): fuori dal catalogo e dai confronti, pagina di dettaglio con promemoria da verificare nel contratto. Solo singola fornitura, no dual fuel.
- `app/routes/` — un blueprint per area; solo HTTP, niente logica di dominio.
- `app/templates/` — Jinja; formattazione numeri/€ nelle macro di `_macros.html`.

## Code Style Guidelines

- Semplice e leggibile; niente astrazioni speculative.
- Logica in `services/`, route sottili. Riusare `forms.parse` e le macro invece di duplicare.
- Commenti solo per il *perché*.

## Gotchas

- **Lettura bollette: LLM solo come ultima risorsa.** `extraction.extract_bill` prova sempre prima `bill_parser`; l'LLM parte solo se mancano i campi essenziali (`bill_parser.REQUIRED`), mai per campi opzionali. Non aggiungere usi dell'LLM (nemmeno riepiloghi) senza chiederlo: la preferenza è evitarlo.
- **Avvio con più worker gunicorn**: le migrazioni girano in ogni worker; `migrations.migrate_database` le serializza con un lock su file (`bollette.db.lock`). Non richiamare `migrate()` direttamente all'avvio: due worker applicherebbero la stessa migrazione (`duplicate column`). `tests/test_migrations.py` lo copre.
- **Immagine Docker**: gira come `1000:100` (non root), `/data` va reso scrivibile da quell'utente (`create_app` fallisce con un messaggio esplicito); gunicorn con `--no-control-socket` (altrimenti prova a scrivere in `/.gunicorn`). Healthcheck su `/health`. Un bind mount con permessi sbagliati è il guasto più comune: vedi `deploy/README.md`.
- **Nuovo campo di `Bill`/`Offer`** = aggiornare insieme: dataclass, una nuova migrazione `NNN_*.sql` (mai modificare quelle esistenti), template del form e (per `Bill`) `FIELD_HELP` in `services/extraction.py`. `tests/test_migrations.py` fallisce se migrazioni e dataclass divergono.
- Il testo estratto da pypdf incolla le celle delle tabelle (es. `2,148,01F1` = potenza 2,1 + 48,01 kWh): le regex di `bill_parser` lo sanno, e ogni campo derivato è controllato (fasce vs totale). Per un nuovo layout aggiungi un test con un estratto anonimo in `tests/fixtures/`, mai PDF o testi con dati personali.
- Codici XML ARERA (`services/arera.py`): significati dedotti dai dati, non da documentazione. Unità non riconosciute → offerta scartata, non indovinata. `source` = `arera:<COD_OFFERTA>` identifica le offerte importate.
- L'offerta attuale nasce dalla bolletta (`source` = `bolletta:<id>`, `bill_parser.parse_offer_terms`) e non sovrascrive mai una marcata «attuale» a mano. Alla rilevazione PUN/PSV delle Impostazioni si riallineano al valore del mese in bolletta (solo per la bolletta più recente).
- Formula luce indicizzata come in bolletta: `(PUN + spread + dispacciamento + capacità) × (1 + perdite)`; `dispatching_extra` si somma dopo.
- Stagionalità: le impostazioni `pun`/`psv` sono **medie annue**; `analysis.analyze` le moltiplica per `season_multiplier` (prezzo medio dell'indice sui mesi di consumo). La proiezione di consumi parziali usa `seasonality.consumption_profile` (profilo tipico, non misurato). Prezzi recenti in `settings` (`pun_recent`, `psv_recent`, `recent_until`, scritti dall'aggiornamento Portale Offerte): adottati solo su richiesta (`/settings/use-recent`); finché `pun == pun_recent` la rilevazione da bolletta non tocca PUN/PSV. Fattori PUN/PSV in `index_factors` (migrazione 005), predefiniti in `seasonality.DEFAULT_INDEX_FACTORS` se mai aggiornati.
- `commodity` vale `power` / `gas` (non italiano) in DB e codice; le etichette sono solo nei template.
- Import in blocco (`/bills/upload` con più file, `bills._bulk_import`): salva solo bollette con tutti i campi essenziali e non duplicate (fornitura+periodo); i PDF scartati vengono cancellati; l'offerta attuale si rileva una volta per fornitura dalla bolletta più recente. `MAX_CONTENT_LENGTH` è 100 MB.
- Offerte luce+gas (`Offer.dual_with` = `source` dell'altra metà): `arera.pair_dual_fuel` le abbina (legame dichiarato `OffertaDual`, poi stesso fornitore + nome a meno di luce/gas, se univoco) e scarta le non abbinabili. `analysis.analyze` le tiene fuori dal confronto singolo (`ranked`) e le valuta in `dual_ranked`; `pricing.pair_bundles` somma le due metà e le confronta con la somma delle due attuali, `verdict.make_dual_verdict` con il risparmio cambiando separatamente. Sconti dual fuel non importati.
- Potenza impegnata (`services/power.py`): usa picco dello storico stampato in bolletta (`annual_max_power_kw`, 12 valori incollati nel testo pypdf) più i picchi mensili successivi; quota potenza €/kW/mese letta dalla bolletta (regolata, senza IVA). Fuori dal confronto offerte.
- **Profili** (migrazione 008): `bills.profile_id` (sempre valorizzato) e `offers.profile_id` (NULL = catalogo condiviso, altrimenti solo di quel profilo: l'offerta attuale). `db.profile_id()` legge il profilo dalla sessione Flask (cookie firmato con `SECRET_KEY`), sempre e solo il db layer filtra: `list_bills/list_offers/get_offer/save_offer/delete_*` sono già scopate, non scrivere query dirette su `bills`/`offers` nelle route. `profile_id` è in `SYSTEM_FIELDS` (mai da form/CSV/LLM). Un'offerta condivisa marcata «attuale» crea una copia del profilo (stessa `source`: nasconde l'originale nell'elenco, vedi `VISIBLE_OFFERS`); `replace_imported_offers` ricarica solo il catalogo condiviso. Località e potenza di default stanno in `profiles` (`PROFILE_SETTINGS`), le altre impostazioni sono globali. Operazioni globali (import ARERA, cron `refresh-offers.sh`) non dipendono dal profilo.
- Durata e fine delle condizioni (migrazione 009): `Offer.duration_months` (DURATA ARERA; -1 indeterminata e 99 altro → None), `started_on` (attivazione, solo per l'offerta attuale, inserita a mano) e due testi del venditore da *mostrare* (`conditions` = condizioni con LIMITANTE 01; `after_term` = frase tipo «Trascorsi 24 mesi…», riconosciuta da regex). I testi non entrano mai nei calcoli. `alerts.terms_end` = attivazione + durata: avviso 60 giorni prima e dopo la fine; dopo l'attivazione sostituisce l'avviso su `expires_on` (che è la scadenza della sottoscrizione in catalogo). Il form deve sempre contenere tutti i campi di `Offer`, altrimenti un salvataggio li azzera.
- Il confronto esclude per costruzione trasporto, oneri, imposte, bonus sociali e canone TV: non aggiungerli.
- `consumption` è kWh per la luce e Smc per il gas (mc × C), sempre già derivato in `Bill.with_derived_consumption`.
- Offerte scadute escluse dal confronto, tranne quella marcata `is_current`. L'offerta attuale è una sola per fornitura (garantito in `db.save_offer`). Offerte con dati insufficienti sono saltate e segnalate, non bloccano il confronto.
- `Offer.zones` (token `R08,P038,C038008`) + località in Impostazioni (`region/province/comune`, testo ISTAT): `pricing.available_in` esclude le offerte con zone che non coprono la località (e tutte quelle con zone se la località è vuota); l'offerta attuale è sempre inclusa. La tabella `settings` ha `value` senza tipo per ospitare anche testo: non reintrodurre `REAL`, convertirebbe `038` in `38.0`.
- `Offer.dispatching_extra`: dispacciamento/capacità fatturati a parte; il confronto aggiunge l'ipotesi `dispatching_extra` (Impostazioni) per confrontare con un'offerta attuale che li include nel prezzo.
- Tutti i prezzi sono in €/kWh o €/Smc; `avg_price`, se presente, ha precedenza sulla formula.

---

## Environment variables

- `DATA_DIR` (default `data`; in Docker `/data`): DB `bollette.db` e `pdf/`
- `SECRET_KEY`, `ANTHROPIC_API_KEY` (opzionale, solo ripiego di lettura), `ANTHROPIC_MODEL`

## Testing policy

Logica di `services/` e parsing coperti da test unitari; flussi principali da smoke test con il client Flask (`tests/test_routes.py`). I bug fix partono da un test di regressione.

## Documentation upkeep

Aggiornare questo file e il README nello stesso task che cambia comandi, layer, env o convenzioni.
