---
name: Bollette self-hosted
description: Lo sportello con il timbro: confronto onesto di luce e gas su foglio menta con pannelli bianchi, un solo accento teal, timbro ambra solo quando conviene cambiare.
colors:
  mint-sheet: "#e8f1ef"
  panel-white: "#ffffff"
  ink: "#1b2a28"
  mute: "#4b5c59"
  rule: "#c5d6d2"
  edge: "#d9e6e3"
  calm-tint: "#eef4f2"
  teal: "#0f766e"
  teal-deep: "#0b5953"
  teal-soft: "#d3ebe7"
  on-teal: "#ffffff"
  notice-yellow: "#fff3cd"
  good-green: "#17722f"
  good-tint: "#e1f3e6"
  bad-red: "#c62828"
  stamp-amber: "#fcd34d"
  stamp-ink: "#111111"
  mint-sheet-night: "#0d1716"
  panel-night: "#152322"
  ink-night: "#e3efec"
  mute-night: "#9bb2ad"
  rule-night: "#2f4542"
  edge-night: "#223633"
  calm-tint-night: "#1b2c2a"
  teal-night: "#4fd1c0"
  teal-deep-night: "#7fe3d6"
  teal-soft-night: "#1c3834"
  on-teal-night: "#04201d"
  notice-yellow-night: "#4a3d10"
  good-green-night: "#4cc473"
  good-tint-night: "#17301f"
  bad-red-night: "#ff7b72"
typography:
  display:
    fontFamily: "Figtree, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, sans-serif"
    fontSize: "2.5rem"
    fontWeight: 800
    lineHeight: 1.15
    letterSpacing: "-0.015em"
  headline:
    fontFamily: "Figtree, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, sans-serif"
    fontSize: "2rem"
    fontWeight: 800
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Figtree, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 700
    lineHeight: 1.3
  body:
    fontFamily: "Figtree, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Figtree, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, sans-serif"
    fontSize: "0.8rem"
    fontWeight: 700
    lineHeight: 1.5
    letterSpacing: "0.04em"
rounded:
  block: "8px"
  field: "12px"
  card: "12px"
  sheet: "16px"
  pill: "999px"
spacing:
  xs: "0.25rem"
  sm: "0.5rem"
  md: "0.75rem"
  lg: "1rem"
  xl: "1.25rem"
  sidebar: "15rem"
  bar: "4.25rem"
components:
  button-primary:
    backgroundColor: "{colors.teal}"
    textColor: "{colors.on-teal}"
    rounded: "{rounded.field}"
    padding: "0.5rem 1.4rem"
    height: "44px"
  button-primary-hover:
    backgroundColor: "{colors.teal-deep}"
  button-secondary:
    backgroundColor: "{colors.teal-soft}"
    textColor: "{colors.teal}"
    rounded: "{rounded.field}"
    padding: "0.5rem 1.4rem"
    height: "44px"
  input:
    backgroundColor: "{colors.panel-white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "0.5rem 0.8rem"
    height: "44px"
  card:
    backgroundColor: "{colors.panel-white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "0.25rem 1.25rem 0.75rem"
  tab-pill:
    backgroundColor: "{colors.panel-white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "0.4rem 1.2rem"
    height: "44px"
  tab-pill-current:
    backgroundColor: "{colors.teal}"
    textColor: "{colors.on-teal}"
  tag:
    backgroundColor: "{colors.calm-tint}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "0.15rem 0.75rem"
  tag-current:
    backgroundColor: "{colors.teal-soft}"
    textColor: "{colors.teal-deep}"
  verdict-block:
    backgroundColor: "{colors.good-tint}"
    textColor: "{colors.ink}"
    rounded: "{rounded.block}"
    padding: "0.9rem 1.1rem 1rem"
  stamp:
    backgroundColor: "{colors.stamp-amber}"
    textColor: "{colors.stamp-ink}"
    rounded: "{rounded.block}"
    padding: "0.2rem 0.8rem 0.3rem"
  nav-item-current:
    backgroundColor: "{colors.teal-soft}"
    textColor: "{colors.teal}"
    rounded: "{rounded.block}"
    height: "3.5rem"
---

# Design System: Bollette self-hosted

## Overview

**Creative North Star: "Lo sportello con il timbro"**

Il sistema deriva dal "quaderno con gli adesivi" di Formando PerCorsi (stesso foglio colorato, pannelli bianchi, ombre morbide, un adesivo che premia) e lo riinterpreta per un confronto di bollette: invece di un quaderno, uno sportello dove si porta il modulo e si riceve un esito. Si distingue dal prodotto fratello per il font (Figtree, non D-DIN, che è commerciale) e per il gesto firma: il timbro ambra, che compare in un solo caso.

Il foglio è menta (#e8f1ef), i pannelli sono bianchi e sollevati da ombre morbide. Un solo accento teal guida: titoli di pagina, azioni, posizione corrente. Verde e rosso dicono solo l'esito (conviene, non conviene, variazione di costo) e mai decorano. Tono sobrio: niente enfasi commerciale, il colore non promette più di quanto il testo dichiari.

**Key Characteristics:**
- Foglio menta, pannelli bianchi, ombre morbide a due strati tinte di teal.
- Un solo accento (teal), usato per guidare; il colore dell'esito è un'altra voce.
- Il timbro ambra ruotato appare solo sulla cifra di "Conviene cambiare".
- Figtree variabile self-hosted, peso 800 per titoli e cifre, numeri tabulari.
- Mobile prima: barra di azioni in basso e foglio "Altro"; da 64rem barra laterale.
- Tema scuro che segue il sistema, con una controparte teal per ogni token.

## Colors

Menta fredda e pannelli bianchi con un teal profondo; ambra solo per il timbro.

### Primary
- **Teal da sportello** (#0f766e): titoli di pagina (nella variante profonda), pulsanti, link, anello di focus, pagina corrente nella navigazione, tab attiva, bordo superiore di 4px su barra alta e barra laterale, logo.
- **Teal profondo** (#0b5953): titoli h1, hover dei pulsanti, testo dei tag "attuale".
- **Teal tenue** (#d3ebe7): riempimento di stato corrente (voce di navigazione, riga attuale, tag attuale), pulsanti secondari, icona nel titolo di fornitura.

### Tertiary
- **Timbro ambra** (#fcd34d) con **inchiostro del timbro** (#111111): solo la cifra del risparmio nel verdetto "Conviene cambiare".

### Neutral
- **Foglio menta** (#e8f1ef): sfondo della pagina.
- **Pannello bianco** (#ffffff): card, tabelle, campi, barre di navigazione.
- **Inchiostro verde** (#1b2a28): testo; **Grigio salvia** (#4b5c59): testo secondario e intestazioni di tabella.
- **Filo** (#c5d6d2) per bordi dei campi; **Bordo tenue** (#d9e6e3) per card e separatori; **Tinta calma** (#eef4f2) per intestazioni di tabella, hover di riga, riquadri di confronto, tag neutri.
- **Avviso giallo** (#fff3cd): messaggi di cautela e tag "da verificare".
- **Verde esito** (#17722f) su **tinta verde** (#e1f3e6) e **Rosso esito** (#c62828): solo l'esito e le variazioni di costo.
- Tema scuro: ogni token ha la sua controparte (foglio #0d1716, pannello #152322, teal #4fd1c0, teal profondo #7fe3d6), nel frontmatter con suffisso `-night`. Non verificato visivamente.

### Named Rules
**The One Guide Rule.** Il teal guida (titoli, azioni, posizione corrente) e niente altro; verde e rosso non sono mai accenti, indicano solo l'esito.
**The Stamp Only Rule.** L'ambra esiste solo come timbro sulla cifra di "Conviene cambiare". Nessun'altra superficie usa l'ambra; i messaggi di cautela usano l'avviso giallo.
**The Color Plus Text Rule.** Ogni stato espresso con il colore è ripetuto dal testo ("Conviene cambiare", "Non conviene cambiare", "attuale").

## Typography

**Display Font:** Figtree variabile (con system-ui, Segoe UI, Roboto)
**Body Font:** Figtree (stessa famiglia)
**Label/Mono Font:** nessuno; solo il testo estratto dal PDF usa il monospace di sistema.

**Character:** Geometrica, aperta, amichevole ma ferma. Figtree è servito da `frontend/src/fonts` (sottoinsieme latino, OFL, nessuna CDN), pesi 300-900.

### Hierarchy
- **Display** (800, 2rem su telefono, 2.5rem da 40rem, 1.15): la cifra del risparmio nel verdetto.
- **Headline** (800, 2rem, 1.15, -0.02em; 1.75rem sotto 40rem): h1 di pagina, in teal profondo.
- **Title** (700, 1.25rem, 1.3): h2 di sezione e riga di sintesi; titolo di fornitura 1.5rem/800.
- **Body** (400, 1rem, 1.5): testo corrente, righe fino a 70ch (58ch per il testo secondario).
- **Label** (700, 0.8rem, 0.04em, maiuscolo): intestazioni di tabella e titoli di sezione dentro le card; secondario 0.875rem.

### Named Rules
**The Tabular Rule.** Ogni importo e ogni colonna numerica usa cifre tabulari, allineate a destra in tabella.
**The Heavy Numbers Rule.** I numeri che sostengono il verdetto sono 800; il corpo resta 400.

## Layout

Mobile prima. Contenuto centrato, massimo 60rem; padding 1rem (0.75rem sotto 40rem), 2rem da 64rem. Ritmo in multipli di 0.25rem: gap 0.5/0.75/1rem, padding card 1.25rem.

Navigazione: da telefono, barra di azioni fissa in basso (4.25rem) con Home, Bollette, Offerte, Confronto e Altro; "Altro" apre un foglio che sale dal basso (Storico, Proposta, Guida, Impostazioni, Profili, cambio profilo) con velo scuro. Sopra, una barra alta con logo e bordo superiore teal di 4px. Da 64rem (>=64rem) la barra diventa una barra laterale sinistra di 15rem, con logo, voci in colonna e cambio profilo in fondo; la barra alta scompare. Griglie di campi `auto-fill` da 14rem; riquadri di confronto `auto-fit` da 10rem. Le tabelle scorrono in orizzontale dentro un pannello. Area di tocco minima 44px.

## Elevation & Depth

Sistema ibrido: il foglio è piatto, i pannelli e gli elementi premibili si sollevano con ombre morbide, a due strati e tinte di teal. L'ombra è strutturale per card, tabelle, campi raggruppati e barre; l'ombra alta compare in risposta (hover, popover, foglio "Altro", barra dei passi).

### Shadow Vocabulary
- **Pannello** (`box-shadow: 0 1px 2px rgb(15 60 56 / .06), 0 6px 18px rgb(15 60 56 / .08)`): card, tabelle, grafici, barre di navigazione, tab a pillola, timbro.
- **Sollevato** (`box-shadow: 0 2px 4px rgb(15 60 56 / .1), 0 12px 28px rgb(15 60 56 / .16)`): hover di pulsanti e tab (con `translateY(-1px)`), popover di spiegazione, foglio "Altro", barra dei passi.
- **Barra in basso** (`box-shadow: 0 -2px 12px rgb(15 60 56 / .12)`): barra mobile; nel tema scuro diventa un filo di 1px.
- Tema scuro: stesse ombre in nero (.4/.35 e .5/.5).

### Named Rules
**The Soft Lift Rule.** Le ombre sono sempre morbide e diffuse, mai con scostamento netto; si alzano al passaggio, tornano piatte alla pressione.

## Shapes

Forme morbide e coerenti: 12px per campi, pulsanti, card, tabelle e popover; 8px per il blocco del verdetto, il timbro, i riquadri di confronto e le voci della barra; 16px per il foglio "Altro" (angoli superiori) e l'angolo basso della barra laterale; pillole complete (999px) per tag e tab. Bordo di 1px in bordo tenue sui pannelli; il timbro ha un bordo di 2px d'inchiostro ed è ruotato di -2 gradi. Icone a tratto uniforme (1.75), in SVG inline che segue il colore del testo.

## Components

### Buttons
- **Shape:** angoli da 12px, minimo 44px di altezza, 6rem di larghezza minima.
- **Primary:** fondo teal, testo bianco, peso 700, padding 0.5rem 1.4rem.
- **Hover / Focus:** fondo teal profondo, sale di 1px con ombra sollevata; alla pressione torna piatto. Focus: anello teal di 2px con scostamento di 2px. Transizione 0.15s, disattivata con riduzione del movimento.
- **Secondary:** fondo teal tenue, testo teal. **Link:** testo grigio, diventa rosso solo per azioni distruttive.

### Chips
- **Tag:** pillola, fondo tinta calma, 0.8rem. "Attuale" in teal tenue con testo teal profondo; "da verificare" in avviso giallo. Il testo ripete sempre lo stato.
- **Tab:** pillole bianche con ombra pannello; la corrente è piena teal con testo bianco, peso 700.

### Cards / Containers
- **Corner Style:** 12px. **Background:** pannello bianco, bordo tenue 1px, ombra pannello. **Padding:** 0.25rem 1.25rem 0.75rem. Titoli di sezione interni in label maiuscolo grigio; titolo di fornitura con icona in cerchio teal tenue.

### Inputs / Fields
- **Style:** 44px, bordo filo 1px, fondo pannello, 12px. **Focus:** bordo teal più anello 2px. Il tastino (i) apre un popover con bordo teal e ombra sollevata.

### Modals
Come in Formando PerCorsi (`frontend/src/components/Modal.tsx`). Sotto 1024px una modale di contenuto è un **foglio dal basso**: bianco, angoli superiori da 8px, alto il 95% (`compact` = alto quanto il contenuto), fondo nero al 50%, sale in 500ms; titolo centrato da 1.5rem. Da 1024px diventa un **riquadro centrale**: angoli 12px, padding 32px, ombra «sopra tutto», fondo grigio scuro al 75%, titolo in accento da 1.25rem. Le **conferme** (`ConfirmModal`, via `useConfirm()`) sono sempre centrali, con «Annulla» tenue e l'azione piena (rossa se distruttiva) affiancati.
Si chiudono tutte con lo stesso `CloseButton`: cerchio tenue da 48px con X in accento (tratto 3), pieno al passaggio. Esc e clic sullo sfondo chiudono; il fuoco resta dentro e torna dov'era.
Si usano dove serve interrompere o proteggere il fuoco: conferme di eliminazione, spiegazioni dei tastini (i), «Dettagli del calcolo», menu «Altro» su telefono, nome del profilo, import del catalogo. Moduli lunghi e la pagina «Insegna» restano pagine.

### Navigation
- Voce corrente: fondo teal tenue e testo teal; inattive in grigio salvia. Mobile: icona sopra etichetta 0.75rem/700 in altezza 3.5rem. Desktop: icona e etichetta in riga, 1rem, hover in tinta calma. Foglio "Altro" con animazione di salita 0.3s.

### Verdict Block (firma)
Blocco da 8px sotto il titolo di fornitura. "Non conviene": tinta calma, etichetta con icona meno. "Conviene cambiare": tinta verde, etichetta verde con icona spunta, e la cifra del risparmio (display, 800) timbrata: fondo ambra, inchiostro nero, bordo 2px, 8px, ombra pannello, rotazione -2 gradi, animazione unica di timbratura di 0.35s (da -7 gradi e scala 1.3), disattivata con riduzione del movimento. Compare solo oltre la soglia di risparmio.

## Do's and Don'ts

### Do:
- **Do** usare il teal (#0f766e) per titoli, azioni e posizione corrente; teal tenue (#d3ebe7) per gli stati correnti.
- **Do** riservare verde e rosso all'esito e ripetere l'esito a parole.
- **Do** mostrare il timbro ambra solo sulla cifra di "Conviene cambiare", una volta sola per verdetto.
- **Do** dare ai pannelli ombra morbida e raggio 12px; 8px al blocco del verdetto; pillole a tag e tab.
- **Do** servire Figtree da `frontend/src/fonts` e usare cifre tabulari per ogni importo.
- **Do** dare a ogni nuovo token chiaro la sua controparte scura.
- **Do** mantenere aree di tocco da 44px e la barra in basso su telefono.

### Don't:
- **Don't** usare l'ambra, né una rotazione o un'animazione di timbratura, per altro che non sia "Conviene cambiare".
- **Don't** usare verde o rosso come accenti decorativi.
- **Don't** caricare font o risorse da CDN, né riusare D-DIN (licenza commerciale).
- **Don't** usare ombre con scostamento netto o bordi spessi sui pannelli (il 2px del timbro e della barra dei passi sono eccezioni dichiarate).
- **Don't** aggiungere un secondo accento accanto al teal.
