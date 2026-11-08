# Bollette self-hosted

> **EN:** a self-hosted web app (Flask + SQLite, one Docker container) for Italian households: upload your electricity and gas bills (PDF, read locally, no cloud needed), import the public offers from the Italian regulator's open-data portal, and find out whether switching supplier would save you money over a year. The UI and docs are in Italian.

App web per raccogliere le bollette di luce e gas, ricavare il consumo annuo e stimare il costo annuo delle offerte di mercato (solo la parte decisa dal fornitore), con il risparmio rispetto all'offerta attuale.

## Avvio

Per installarla su un NAS o home server (compose, permessi, backup, aggiornamento offerte) vedi [`deploy/`](deploy/README.md).

```bash
# sviluppo
uv sync && uv run flask --app "app:create_app()" run --debug

# Docker (NAS)
cp .env.example .env   # opzionale: ANTHROPIC_API_KEY, solo come ripiego di lettura PDF
docker compose up --build   # http://localhost:8080, dati in ./data
```

## Test

```bash
uv run pytest
```

## Come si usa

1. **Carica le bollette** (PDF di luce e gas): l'app legge i dati, ricava l'**offerta attuale** (spread, perdite di rete, dispacciamento, capacità, quota fissa, PUN/PSV del mese) e li mostra da confermare. Puoi selezionare **più PDF insieme**: quelli letti per intero e non già presenti (stessa fornitura e periodo) vengono salvati subito, gli altri sono elencati e si inseriscono uno per uno.
2. **Importa le offerte** dal Portale Offerte (una volta ogni tanto, pulsante in *Offerte*).
3. **Home**: per luce e gas dice se conviene cambiare, con quale offerta, quanto si risparmia in un anno, e se il vantaggio regge con PUN/PSV ±20%. Soglia: almeno 30 € e 5% l'anno.

Se hai già un'offerta attuale inserita a mano, le nuove bollette non la sovrascrivono; il pulsante «usa come offerta attuale» in *Bollette* forza la rilevazione.

## Finestra temporale e stagionalità

- Il confronto ragiona su **12 mesi interi**. Il consumo annuo è quello stampato nella bolletta più recente (che copre già gli ultimi 12 mesi); un mese con poco consumo non sposta il verdetto.
- Se il dato annuo manca, i consumi noti sono proiettati a 12 mesi con un **profilo stagionale tipico** (il gas d'inverno pesa molto più che d'estate) e, sotto i 330 giorni coperti, l'app avverte che la stima è poco affidabile.
- PUN e PSV nelle Impostazioni sono **medie annue**. Il confronto le adatta ai mesi in cui consumi, usando la stagionalità storica dei prezzi (ultimi 3 anni completi dal CSV del Portale Offerte, aggiornato col pulsante *Aggiorna dal Portale Offerte*; senza aggiornamento valgono valori predefiniti 2023-2025). Alla lettura di una bolletta, il PUN/PSV del mese viene riportato a media annua dividendo per il fattore del mese. In *Impostazioni*, dopo l'aggiornamento dal Portale Offerte, puoi adottare i **prezzi recenti** (media degli ultimi 3 mesi del CSV, destagionalizzata): sono più freschi della bolletta ma estrapolano il trend, e se li adotti le bollette successive non li sovrascrivono.

## Lettura delle bollette

1. **Parser a regole** (locale, gratuito): legge le etichette standard ARERA e controlla la coerenza dei dati (es. le fasce devono sommare al consumo). Gestito con le bollette di Energia Pulita/Antenore; altri fornitori con lo stesso standard dovrebbero funzionare.
2. **Layout di lettura** (locale, gratuito): regole «etichetta → valore» per altri fornitori. Quelli forniti con l'app stanno in `app/layouts/*.json`; quelli che insegni tu sono salvati nel database.
3. **LLM, solo se mancano ancora i campi essenziali** (fornitura, periodo, consumo, totale) e solo se `ANTHROPIC_API_KEY` è impostata: in quel caso il testo della bolletta (dati personali) esce dal NAS. Con tutti i campi essenziali trovati l'LLM non viene mai chiamato.
4. Altrimenti modulo manuale, precompilato con quanto letto.

### La tua bolletta non si legge?

Carica il PDF da solo: l'app propone **«Insegna all'app a leggerlo»**. Selezioni nel testo del PDF i valori (periodo, consumo, totale…) e l'app ricava dove si trovano; dalla bolletta successiva dello stesso fornitore la lettura è automatica. In *Bollette → Layout di lettura* puoi vedere o eliminare i layout.

Se vuoi che il tuo fornitore funzioni per tutti, *Segnala agli sviluppatori* mostra prima il file che verrebbe condiviso: **solo etichette e formati, mai valori, nomi o indirizzi** (le etichette con dati sospetti sono escluse). Non parte nulla in automatico: lo invii tu, per esempio con la segnalazione GitHub già compilata. Per chi mantiene il progetto: vedi `app/layouts/README.md`.

## Profili (più appartamenti)

Non sono account: non c'è login. Un **profilo** è un appartamento, con le sue bollette, la sua offerta attuale, la località e la potenza di default. Si crea e si cambia da *Profili* (o dal menu in alto); la scelta resta nel cookie del browser. Il catalogo delle offerte (importate o inserite a mano) e le ipotesi su PUN/PSV sono condivisi. Cancellare un profilo elimina le sue bollette e i PDF. I dati esistenti passano nel profilo «Casa».

## Offerte

- A mano, da CSV (`examples/offers.csv`) o dal **Portale Offerte** (open data Acquirente Unico/ARERA, pulsante in *Offerte*): scarica i file XML pubblici (~35 MB) e importa le offerte domestiche; sostituisce le precedenti importate, tenendo quelle a mano e l'«attuale».
- Non importati: sconti e bonus una tantum (anche quelli «dual fuel»), offerte con fasce particolari.
- **Guida e spiegazioni**: la voce *Guida* spiega in modo semplice fisso/indicizzato, PUN/PSV, fasce, quote e come leggere il verdetto; accanto ai termini di form e tabelle c'è un tastino (i) con la spiegazione.
- **Valuta una proposta** (menu *Proposta*): se un operatore ti propone un'offerta fuori catalogo, inserisci prezzi, quote e bonus che ti dice e vedi costo annuo, risparmio (primo anno e senza bonus) e sensibilità a PUN/PSV ±20% rispetto alla tua offerta attuale. Puoi salvarla: la pagina della proposta riassume ciò che deve comparire nel contratto (prezzi, quote, bonus, durata, tue note sulle promesse a voce) più le domande da chiudere prima di firmare. Le proposte salvate non entrano nel catalogo né nei confronti; luce e gas si valutano una alla volta.
- **Luce + gas insieme**: le offerte dual fuel sono importate come due metà (luce e gas) abbinate; valgono solo sottoscritte insieme, quindi non compaiono nel confronto della singola fornitura. La home e la pagina *Confronto → Luce + gas insieme* le confrontano con la somma delle tue due offerte attuali e con il risparmio che avresti cambiando le due forniture separatamente. Il venditore dichiara l'abbinamento solo per alcune: le altre si abbinano per fornitore e nome (a meno di «luce»/«gas»); le non abbinabili sono scartate e contate nel messaggio di import.
- **Durata e fine delle condizioni**: per le offerte importate l'app mostra durata, condizioni dichiarate dal venditore (nuovi clienti, addebito su conto...) e cosa cambia dopo il periodo. Se ne attivi una, marcala «attuale» e indica la data di attivazione (*Offerte*, modifica): 60 giorni prima della fine delle condizioni la Home ti avvisa che il prezzo può cambiare e di confrontare le offerte.
- **Potenza impegnata**: se in bolletta c'è lo storico dei picchi di potenza prelevata (12 mesi), la home dice se puoi scendere di livello (1,5 · 3 · 4,5 · 6 … kW) e quanto risparmieresti di quota potenza. Il suggerimento è prudente (il picco massimo deve stare nel nuovo livello) e avvisa se il margine è ridotto o se i mesi osservati sono pochi.
- **Zona**: le offerte limitate a certe aree (codici ISTAT nel file) compaiono nel confronto solo se coprono la località impostata in *Impostazioni* (default Ferrara: regione 08, provincia 038, comune 038008).
- I codici dell'XML non sono documentati ufficialmente: la decodifica è in `app/services/arera.py` ed è dedotta dai dati.

## Database

Migrazioni SQL numerate in `app/migrations/`, applicate all'avvio (versione in `PRAGMA user_version`). Per modificare lo schema aggiungi `NNN_descrizione.sql`; non modificare quelle già pubblicate.

## Limiti

- È una stima, non un preventivo. Per le offerte indicizzate usa PUN/PSV assunti (Impostazioni).
- I prezzi futuri di PUN/PSV non sono noti: la stagionalità è storica e non prevede trend (nel 2026 sono saliti). Il verdetto mostra la sensibilità a ±20%.
- Dispacciamento e oneri di capacità: molte offerte li fatturano a parte al costo regolato; si assume un valore (Impostazioni) per renderle confrontabili con l'offerta attuale.
- Alcune offerte valgono solo in certe aree ma l'XML non lo dichiara (es. «Dedicata Comune»): controlla sempre le condizioni sul sito del venditore.
- Nessuna autenticazione: tenere solo in rete locale.

## Licenza

Apache-2.0, vedi [LICENSE](LICENSE). I dati delle offerte provengono dagli [open data del Portale Offerte](https://www.ilportaleofferte.it/portaleOfferte/it/open-data.page) (uso libero); l'app non è affiliata ad ARERA né ad Acquirente Unico.
