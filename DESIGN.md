---
name: Bollette self-hosted
description: Sportello chiaro per il confronto delle offerte luce/gas: sistema, piatto, un solo accento blu, colore solo per l'esito.
colors:
  paper: "#f6f7f9"
  surface: "#ffffff"
  ink: "#1d2330"
  mute: "#5f6675"
  rule: "#d9dce3"
  accent-blue: "#1a66e0"
  notice-yellow: "#fff3cd"
  good-green: "#17722f"
  bad-red: "#c62828"
  good-tint: "#e9f5ec"
  calm-tint: "#eef0f4"
  paper-night: "#14171f"
  surface-night: "#1a1e29"
  ink-night: "#e6e8ee"
  mute-night: "#9aa3b5"
  rule-night: "#303646"
  accent-blue-night: "#6aa3ff"
  notice-yellow-night: "#4a3d10"
  good-green-night: "#4cc473"
  bad-red-night: "#ff7b72"
  good-tint-night: "#16301f"
  calm-tint-night: "#232838"
typography:
  body:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  headline:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
  nav:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, sans-serif"
    fontSize: "1rem"
    fontWeight: 500
    lineHeight: 1.5
rounded:
  sm: "6px"
  md: "8px"
spacing:
  xs: "0.2rem"
  sm: "0.4rem"
  md: "0.75rem"
  lg: "1rem"
components:
  button-primary:
    backgroundColor: "{colors.accent-blue}"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "0.4rem 0.5rem"
  input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "0.4rem 0.5rem"
  card:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "0.25rem 1rem"
  flash-warn:
    backgroundColor: "{colors.notice-yellow}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "0.6rem 0.9rem"
---

# Design System: Bollette self-hosted

## Overview

**Creative North Star: "Lo sportello chiaro"**

Un modulo ufficiale fatto bene: ordinato, affidabile, leggibile da chi non è tecnico. L'interfaccia non vende nulla; presenta un verdetto e i numeri che lo sostengono, in italiano, con tono sobrio. Usa i font e i controlli del sistema, bordi sottili al posto delle ombre e una sola voce cromatica.

Il colore dice l'esito, non decora: il blu segna link e azione, verde e rosso dicono se conviene, il giallo avvisa; le informazioni restano neutre. Tutto il resto è carta e inchiostro. Il tema scuro segue le preferenze del sistema e ha una controparte per ogni colore.

La direzione dichiarata è «piatto ma più morbido»: la struttura resta piatta e senza ombre, e le prossime modifiche possono allargare un poco raggi e spaziature. I valori qui sotto sono quelli attuali.

**Key Characteristics:**
- Font di sistema, nessun web font, nessuna risorsa esterna.
- Un solo accento (blu); verde/rosso/giallo solo per l'esito.
- Piatto ma non su un solo piano: nessuna ombra, la profondità viene dal tono (pagina grigio chiarissimo, riquadri bianchi) e da bordi da 1px.
- Colonna unica fino a 60rem, pensata anche per il telefono.
- Numeri tabulari allineati a destra.

## Colors

Carta e inchiostro neutri con un blu funzionale; la palette ha una versione scura speculare.

### Primary
- **Blu funzionale** (`#1a66e0`, notte `#6aa3ff`): contrasto 4,8:1 sulla pagina in chiaro: link e pulsante principale. Nient'altro.

### Neutral
- **Carta** (`#f6f7f9`, notte `#14171f`): sfondo pagina.
- **Superficie** (`#ffffff`, notte `#1a1e29`): riquadri, gruppi di campi, campi e menu. Dà profondità senza ombre.
- **Inchiostro** (`#1d2330`, notte `#e6e8ee`): testo e voci di navigazione.
- **Grigio sommesso** (`#5f6675`, notte `#9aa3b5`, un blu-grigio senza la deriva viola precedente): note, etichette secondarie (`.muted`, 0.875rem).
- **Filo** (`#d9dce3`, notte `#303646`): bordi, righe di tabella, separatori.

### Semantic
- **Verde esito** (`#17722f`, notte `#4cc473`): risparmio, «conviene».
- **Rosso esito** (`#c62828`, notte `#ff7b72`): costo in più, azioni distruttive (pulsante `link`).
- **Tinta verdetto** (`#e9f5ec` / neutra `#eef0f4`, notte `#16301f` / `#1d212c`): fondo del solo blocco del verdetto, verde se conviene, neutro se non conviene.
- **Giallo avviso** (`#fff3cd`, notte `#4a3d10`): sfondo dei messaggi `warn`.

### Named Rules
**The Outcome-Only Color Rule.** Verde, rosso e giallo compaiono solo per comunicare un esito o un avviso, mai come decorazione.
**The One Voice Rule.** Il blu è l'unico accento: resta su link, azione primaria e il segno «attuale».

## Typography

**Display/Body/Label Font:** `system-ui, sans-serif`

**Character:** nativa e neutra; ogni dispositivo mostra il proprio font di sistema, quindi niente da scaricare e nessun carattere «di marca».

### Hierarchy
- **Titolo pagina** (700, 1.75rem, 1.2, tracking -0.01em): `h1`; il profilo attivo è un sottotitolo da 0.875rem sotto.
- **Titolo sezione** (600, 1.25rem): `h2`; stessa dimensione per l'etichetta del verdetto («Conviene cambiare», 700).
- **Etichetta di gruppo** (600, 0.8rem, maiuscolo, tracking 0.06em, grigio sommesso): titoli dei gruppi nei form.
- **Titolo di riquadro in Home** (`.card.commodity`: 600, 1.25rem, inchiostro) con sotto una riga di contesto `.card-meta` (consumo annuo, giorni di bollette). Sopra i riquadri, una frase di sintesi (`.summary`, 600, 1.25rem). Nel «Non conviene» la cifra grande non c'è: il risparmio massimo sta nella nota.
- **Verdetto** (700, 2rem; 2.5rem da 40rem in su, tracking -0.015em, cifre tabulari): la cifra del risparmio.
- **Body** (400, 1rem = la dimensione scelta dall'utente nel browser, 1.5; 1.55 con tracking 0.005em in tema scuro): tutto il resto. Paragrafi e liste a 70ch al massimo; titoli con `text-wrap: balance`, testo con `text-wrap: pretty`.
- **Nav** (500, 1rem; 700 per la pagina corrente): voci del menu principale.
- **Note e etichette dei campi** (400, 0.875rem; le note in grigio sommesso): `.muted`, `label`.
- **Intestazioni di tabella** (600, 0.8rem, maiuscolo, tracking 0.04em, grigio sommesso).
- **Numeri** (`font-variant-numeric: tabular-nums`, a destra): ogni colonna di cifre (`.num`).

### Named Rules
**The Scale Rule.** Sei dimensioni e quattro pesi, e nessun valore nuovo senza un ruolo nuovo: 0.8 (etichette maiuscole, intestazioni, segni), 0.875 (note, etichette dei campi), 1 (testo), 1.25 (titoli di sezione), 1.75 (titolo di pagina), 2–2.5 (cifra del verdetto); pesi 400, 500, 600, 700. Le dimensioni sono in `rem` per rispettare le impostazioni dell'utente.
**The Tabular Rule.** Importi e consumi usano cifre tabulari e allineamento a destra, così si confrontano in colonna.

## Layout

Una colonna centrata, `max-width: 60rem`, padding 1rem (0.75rem sotto 40rem); il menu si allinea alla stessa colonna. Ordine della Home: prima i verdetti (luce, gas, luce+gas), uno accanto all'altro; dopo i consigli secondari (potenza impegnata); in fondo le azioni e l'avvertenza unica. Le azioni rare stanno in cima in un `<details>` (aggiorna o importa il catalogo, aperto solo se il catalogo è vuoto), non sotto 50 righe di tabella.

Il selettore del profilo compare solo se i profili sono più d'uno; con uno solo restano il link «Profili» a destra e nessun sottotitolo sotto il titolo: sul telefono si risparmia una riga di menu. Il cambio di fornitura (Luce / Gas / Luce + gas insieme) in Confronto e Storico usa schede (`.tabs`), non link separati da puntini.

I moduli sono griglie `repeat(auto-fill, minmax(14rem, 1fr))` con gap 0.75rem; `.full` occupa la riga intera e i gruppi hanno un titolo `h2`. Le tabelle stanno in un contenitore `.scroll` che occupa tutta la colonna e scorre in orizzontale sul telefono. Nei riquadri dei verdetti «Dettagli del calcolo» e «Vedi tutte le offerte» stanno sulla stessa riga (`.card-links`) quando c'è spazio, e i dettagli aperti prendono tutta la larghezza. Nella pagina Profili ogni profilo è un riquadro (nome e «Rinomina» in riga, poi conteggio e azioni) e non una tabella: sul telefono le azioni restano a portata. Ritmo verticale: margini da 1rem tra riquadri e fieldset.

## Elevation & Depth

Piatto per scelta, ma non su un solo piano. Nessuna ombra: la profondità viene dal tono (pagina grigio chiarissimo, riquadri e gruppi di campi su Superficie) e da bordi di 1px nel colore Filo. Gli stati cambiano colore, non quota.

### Named Rules
**The Flat-By-Default Rule.** «Piatto» vuol dire senza ombre né sfocature, non su un solo piano: per distinguere un blocco usa la Superficie, un bordo o uno spazio.

## Shapes

Angoli appena arrotondati: 6px su campi, pulsanti e messaggi; 8px su riquadri (`.card`) e fieldset. Nessuna forma decorativa, nessuna pillola. Bordi sempre da 1px.

## Components

### Buttons
- **Shape:** 6px, senza bordo.
- **Primary:** fondo blu, testo bianco in chiaro e quasi nero (`#0b1220`) in scuro per mantenere contrasto 4,5:1, padding 0.4rem 0.5rem, font ereditato.
- **Link-style (distruttivo):** `button.link`, senza fondo né padding, testo grigio sommesso; diventa rosso solo al passaggio del mouse o con il focus. Il rosso sta per l'intenzione di cancellare, non per ogni riga; la conferma resta.
- **Focus:** anello blu da 2px con scarto 2px su ogni elemento (`:focus-visible`). Altezza minima 44px. `a.btn` ha lo stesso aspetto per le azioni in forma di link.

### Inputs / Fields
- **Style:** bordo Filo 1px, fondo Carta, testo Inchiostro, raggio 6px, font ereditato.
- **Label:** colonna con gap 0.2rem, 0.875rem, sopra il campo.
- **Focus:** anello blu da 2px (`:focus-visible`).

### Cards / Containers
- **Corner Style:** 8px, bordo Filo 1px, padding 0.25rem 1rem, margine 1rem. Nessuna ombra.

### Messages (flash)
- Riquadro 6px, padding 0.6rem 0.9rem; `warn` su giallo; `info` senza fondo, con bordo Filo e testo sommesso da 0.875rem.

### Navigation
- Sotto 48rem le voci stanno dietro il pulsante «Menu» (elenco verticale, pagina corrente su fondo neutro, Esc chiude).
- Riga in alto su Superficie con bordo inferiore Filo; voci in Inchiostro, peso 500, area di tocco almeno 44px; la pagina corrente (`aria-current=page`) è in grassetto con sottolineatura blu da 3px. Selettore profilo con pulsante «Cambia» solo se i profili sono più d'uno; altrimenti solo il link «Profili» a destra.

### Tabs
- Per cambiare vista dentro una pagina (Luce / Gas / Luce + gas insieme): riga con filo Filo sotto, voci alte 44px, quella corrente in grassetto con sottolineatura blu da 3px.

### Verdict
- Blocco con fondo tenue (raggio 6px, nessuna ombra) in testa al riquadro: etichetta in grassetto («Conviene cambiare» / «Non conviene cambiare»), cifra del risparmio a 2rem, grassetto, cifre tabulari, nota sotto. L'esito si legge dal testo, non solo dal colore.

### Icons
- SVG inline dalla macro `icon()` in `_macros.html` (nessun font, nessuna risorsa esterna): tratto 1.75, `currentColor`, 1.25rem, `aria-hidden`. Servono a riconoscere, mai a decorare: fornitura nei titoli dei riquadri (fulmine, fiamma, quadrante; in grigio sommesso), esito nel verdetto (spunta / meno, nel colore dell'etichetta), triangolo negli avvisi. Il testo resta sempre presente.
- Tastino (i): icona `info` blu senza bordo, dopo il termine che spiega (mai prima), con `U+2060` per non andare a capo da solo; area di tocco 44px.

### Charts
- Chart.js locale (`static/vendor`), una serie per grafico in blu accento (dati, non decorazione), griglia in Filo, nessuna legenda; barre più chiare = lettura stimata. Il dettaglio sta nella tabella sotto.

### Details
- `<details>` per calcoli, condizioni e spiegazioni (PUN/PSV); il sommario è blu, alto almeno 44px.

### Tags (segni di stato)
- Piccolo riquadro da 0.8rem, raggio 6px, padding 0.2rem 0.6rem, con il testo in grassetto 600: il colore dice lo stato, il testo lo ripete.
- **attuale** (`.tag.current`): testo e bordo blu; la riga corrispondente prende il tono neutro (`tr.current`).
- **da verificare**, per esempio «stimata» (`.tag.warn`): fondo Giallo avviso, testo Inchiostro, senza bordo.

### Tables
- Celle allineate a sinistra, padding 0.4rem 0.6rem, solo bordo inferiore; colonne numeriche a destra con cifre tabulari. Passando il mouse la riga prende il tono neutro; la riga dell'offerta attuale lo ha sempre.
- Su telefono la prima colonna può andare a capo. Un filo di 1px blu sul bordo da cui la tabella scorre (animazione a scorrimento, senza gradienti) segnala che c'è altro; dove il browser non la supporta resta solo il testo tagliato.

### Pager
- Riga flessibile con gap 0.75rem (`.pager`).

## Do's and Don'ts

### Do:
- **Do** usare i token `--bg`, `--surface`, `--fg`, `--muted`, `--line`, `--accent`, `--warn`, `--good`, `--bad` e fornire sempre il valore scuro.
- **Do** mostrare l'esito in verde o rosso e accompagnarlo con testo (non solo colore).
- **Do** mantenere bordi da 1px e raggi 6px/8px; eventuali ammorbidimenti restano piccoli e uniformi.
- **Do** riusare le macro di `_macros.html` per numeri ed euro.

### Don't:
- **Don't** introdurre ombre, gradienti, web font o risorse da CDN.
- **Don't** mettere i riquadri sullo stesso tono della pagina: usano `--surface`.
- **Don't** usare il blu per decorare titoli o riquadri.
- **Don't** usare colori semantici come ornamento.
- **Don't** aggiungere un tono commerciale (badge «offerta!», urgenza, enfasi promozionale): il confronto deve restare sobrio e dichiarare incertezza ed esclusioni.
