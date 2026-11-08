---
name: Bollette self-hosted
description: Sportello chiaro per il confronto delle offerte luce/gas: sistema, piatto, un solo accento blu, colore solo per l'esito.
colors:
  paper: "#fafafa"
  ink: "#1d2330"
  mute: "#666677"
  rule: "#ddddee"
  accent-blue: "#1f6feb"
  notice-yellow: "#fff3cd"
  notice-blue: "#e7f1ff"
  good-green: "#1a7f37"
  bad-red: "#c62828"
  good-tint: "#e9f5ec"
  calm-tint: "#eef0f4"
  paper-night: "#14171f"
  ink-night: "#e6e8ee"
  mute-night: "#9988aa"
  rule-night: "#2c3140"
  accent-blue-night: "#6aa3ff"
  notice-yellow-night: "#4a3d10"
  notice-blue-night: "#1b2b45"
  good-green-night: "#4cc473"
  bad-red-night: "#ff7b72"
  good-tint-night: "#16301f"
  calm-tint-night: "#1d212c"
typography:
  body:
    fontFamily: "system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.5
  headline:
    fontFamily: "system-ui, sans-serif"
    fontSize: "1.15rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "system-ui, sans-serif"
    fontSize: "0.9rem"
    fontWeight: 400
    lineHeight: 1.5
  nav:
    fontFamily: "system-ui, sans-serif"
    fontSize: "16px"
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
  flash-info:
    backgroundColor: "{colors.notice-blue}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "0.6rem 0.9rem"
---

# Design System: Bollette self-hosted

## Overview

**Creative North Star: "Lo sportello chiaro"**

Un modulo ufficiale fatto bene: ordinato, affidabile, leggibile da chi non è tecnico. L'interfaccia non vende nulla; presenta un verdetto e i numeri che lo sostengono, in italiano, con tono sobrio. Usa i font e i controlli del sistema, bordi sottili al posto delle ombre e una sola voce cromatica.

Il colore dice l'esito, non decora: il blu segna link e azione, verde e rosso dicono se conviene, giallo e azzurro pallido avvisano e informano. Tutto il resto è carta e inchiostro. Il tema scuro segue le preferenze del sistema e ha una controparte per ogni colore.

La direzione dichiarata è «piatto ma più morbido»: la struttura resta piatta e senza ombre, e le prossime modifiche possono allargare un poco raggi e spaziature. I valori qui sotto sono quelli attuali.

**Key Characteristics:**
- Font di sistema, nessun web font, nessuna risorsa esterna.
- Un solo accento (blu); verde/rosso/giallo solo per l'esito.
- Piatto: bordi da 1px, nessuna ombra.
- Colonna unica fino a 60rem, pensata anche per il telefono.
- Numeri tabulari allineati a destra.

## Colors

Carta e inchiostro neutri con un blu funzionale; la palette ha una versione scura speculare.

### Primary
- **Blu funzionale** (`#1f6feb`, notte `#6aa3ff`): link e pulsante principale. Nient'altro.

### Neutral
- **Carta** (`#fafafa`, notte `#14171f`): sfondo pagina e campi.
- **Inchiostro** (`#1d2330`, notte `#e6e8ee`): testo e voci di navigazione.
- **Grigio sommesso** (`#666677`, notte `#9988aa`): note, etichette secondarie (`.muted`, 0.9rem).
- **Filo** (`#ddddee`, notte `#2c3140`): bordi, righe di tabella, separatori.

### Semantic
- **Verde esito** (`#1a7f37`, notte `#4cc473`): risparmio, «conviene».
- **Rosso esito** (`#c62828`, notte `#ff7b72`): costo in più, azioni distruttive (pulsante `link`).
- **Tinta verdetto** (`#e9f5ec` / neutra `#eef0f4`, notte `#16301f` / `#1d212c`): fondo del solo blocco del verdetto, verde se conviene, neutro se non conviene.
- **Giallo avviso** (`#fff3cd`, notte `#4a3d10`): sfondo dei messaggi `warn`.
- **Azzurro info** (`#e7f1ff`, notte `#1b2b45`): sfondo dei messaggi `info`.

### Named Rules
**The Outcome-Only Color Rule.** Verde, rosso, giallo e azzurro compaiono solo per comunicare un esito o un avviso, mai come decorazione.
**The One Voice Rule.** Il blu è l'unico accento: resta su link e azione primaria.

## Typography

**Display/Body/Label Font:** `system-ui, sans-serif`

**Character:** nativa e neutra; ogni dispositivo mostra il proprio font di sistema, quindi niente da scaricare e nessun carattere «di marca».

### Hierarchy
- **Headline** (400, 1.15rem, 1.5): frase del verdetto in Home (`.headline`).
- **Body** (400, 16px, 1.5): tutto il resto.
- **Nav** (500, 16px): voci del menu principale.
- **Label** (400, 0.9rem): etichette dei campi e note (`.muted`).
- **Numeri** (`font-variant-numeric: tabular-nums`, a destra): ogni colonna di cifre (`.num`).

### Named Rules
**The Tabular Rule.** Importi e consumi usano cifre tabulari e allineamento a destra, così si confrontano in colonna.

## Layout

Una colonna centrata, `max-width: 60rem`, padding 1rem (0.75rem sotto 40rem). Il menu è una riga flessibile con gap 1rem che va a capo sul telefono; il selettore del profilo sta a destra (`margin-left: auto`). I moduli sono griglie `repeat(auto-fill, minmax(14rem, 1fr))` con gap 0.75rem; `.full` occupa la riga intera. Le tabelle scorrono in orizzontale dentro la pagina (`overflow-x: auto`, celle `nowrap`) invece di rompere il layout. Ritmo verticale: margini da 1rem tra riquadri e fieldset.

## Elevation & Depth

Piatto per scelta. Nessuna ombra: la separazione viene da bordi di 1px nel colore Filo e dallo spazio. Gli stati cambiano colore, non quota.

### Named Rules
**The Flat-By-Default Rule.** Non aggiungere ombre né sfocature; per distinguere un blocco usa un bordo o uno spazio.

## Shapes

Angoli appena arrotondati: 6px su campi, pulsanti e messaggi; 8px su riquadri (`.card`) e fieldset. Nessuna forma decorativa, nessuna pillola. Bordi sempre da 1px.

## Components

### Buttons
- **Shape:** 6px, senza bordo.
- **Primary:** fondo blu, testo bianco in chiaro e quasi nero (`#0b1220`) in scuro per mantenere contrasto 4,5:1, padding 0.4rem 0.5rem, font ereditato.
- **Link-style (distruttivo):** `button.link`, senza fondo né padding, testo rosso.
- **Focus:** anello blu da 2px con scarto 2px su ogni elemento (`:focus-visible`). Altezza minima 44px. `a.btn` ha lo stesso aspetto per le azioni in forma di link.

### Inputs / Fields
- **Style:** bordo Filo 1px, fondo Carta, testo Inchiostro, raggio 6px, font ereditato.
- **Label:** colonna con gap 0.2rem, 0.9rem, sopra il campo.
- **Focus:** anello blu da 2px (`:focus-visible`).

### Cards / Containers
- **Corner Style:** 8px, bordo Filo 1px, padding 0.25rem 1rem, margine 1rem. Nessuna ombra.

### Messages (flash)
- Riquadro 6px, padding 0.6rem 0.9rem; `warn` su giallo, `info` su azzurro.

### Navigation
- Riga in alto con bordo inferiore Filo; voci in Inchiostro, peso 500, senza sottolineatura. Profilo attivo e link «Profili» a destra. Nessuno stato attivo distinto oggi.

### Verdict
- Blocco con fondo tenue (raggio 6px, nessuna ombra) in testa al riquadro: etichetta in grassetto («Conviene cambiare» / «Non conviene cambiare»), cifra del risparmio a 2rem, grassetto, cifre tabulari, nota sotto. L'esito si legge dal testo, non solo dal colore.

### Details
- `<details>` per calcoli, condizioni e spiegazioni (PUN/PSV); il sommario è blu, alto almeno 44px.

### Tables
- Intestazioni e celle allineate a sinistra, padding 0.4rem 0.6rem, solo bordo inferiore; colonne numeriche a destra con cifre tabulari.

- Su telefono la prima colonna può andare a capo; un'ombra sul bordo segnala che la tabella scorre di lato.

### Pager
- Riga flessibile con gap 0.75rem (`.pager`).

## Do's and Don'ts

### Do:
- **Do** usare i token `--bg`, `--fg`, `--muted`, `--line`, `--accent`, `--warn`, `--info`, `--good`, `--bad` e fornire sempre il valore scuro.
- **Do** mostrare l'esito in verde o rosso e accompagnarlo con testo (non solo colore).
- **Do** mantenere bordi da 1px e raggi 6px/8px; eventuali ammorbidimenti restano piccoli e uniformi.
- **Do** riusare le macro di `_macros.html` per numeri ed euro.

### Don't:
- **Don't** introdurre ombre, gradienti, web font o risorse da CDN.
- **Don't** usare il blu per decorare titoli o riquadri.
- **Don't** usare colori semantici come ornamento.
- **Don't** aggiungere un tono commerciale (badge «offerta!», urgenza, enfasi promozionale): il confronto deve restare sobrio e dichiarare incertezza ed esclusioni.
