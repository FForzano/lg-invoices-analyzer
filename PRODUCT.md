# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Persone che gestiscono la propria casa in Italia e hanno un NAS o home server: l'autore e altri self-hoster (il repo è pubblico). Usano l'app a casa, in rete locale, di rado: dopo l'arrivo di una bolletta o quando valutano se cambiare fornitore di luce/gas. Spesso la consultano dal telefono, con la bolletta in mano. Chi la usa non è necessariamente tecnico; l'installazione è fatta una volta sola.

## Product Purpose

Raccogliere le bollette di luce e gas (PDF letti in locale), ricavare il consumo annuo e stimare il costo annuo delle offerte di mercato (solo la parte decisa dal fornitore), dicendo se conviene cambiare, con quale offerta e quanto si risparmia in un anno. Successo: l'utente capisce a colpo d'occhio il verdetto e si fida della stima.

## Positioning

Self-hosted: i dati personali delle bollette restano in casa; l'LLM è solo ultima risorsa e opzionale. Confronta sul costo reale annuo (stagionalità, sensibilità PUN/PSV ±20%, soglia minima di risparmio) invece di mostrare un elenco di tariffe.

## Operating Context

Un container Docker (Flask + SQLite) su NAS/Raspberry Pi, senza login. Flusso: carica bollette (anche più PDF insieme) → importa offerte dal Portale Offerte ARERA → Home con il verdetto per luce e gas (e luce+gas insieme), consiglio sulla potenza impegnata. Più profili = più appartamenti, scelti da cookie.

## Capabilities and Constraints

- Il confronto esclude per costruzione trasporto, oneri, imposte, bonus sociali e canone TV.
- Verdetto «conviene» se risparmio ≥ 30 € e ≥ 5% l'anno; avvisa quando la stima è poco affidabile (meno di ~330 giorni coperti).
- Commodity `power` / `gas` nel codice; etichette italiane solo nei template.
- Front-end React + TypeScript (Vite, Tailwind) in `frontend/`, che parla con l'API JSON di Flask (`/api`); Flask serve il build. Scelto per poter incapsulare l'app in una nativa (Capacitor, in futuro). Nessun login per ora: il codice lo prevede (`authenticate()`, `RequireAuth`) ma resta spento.

## Brand Commitments

UI e testi in italiano. Tono sobrio e onesto: dichiarare cosa il confronto esclude e quanto è incerta una stima, senza enfasi commerciale.

## Evidence on Hand

Nessun dato reale di utenti nel repo: i test usano estratti anonimi in `tests/fixtures/`; mai PDF o testi con dati personali. Non inventare risparmi, offerte o fornitori di esempio.

## Product Principles

1. Il verdetto viene prima dei dettagli; i numeri che lo sostengono sono a un passo.
2. Onestà sull'incertezza: mostrare esclusioni, ipotesi e affidabilità della stima.
3. Privacy per default: tutto locale, nessuna risorsa esterna non necessaria.
4. Usabile da telefono, in pochi minuti, da chi non è tecnico.
5. Semplice e leggibile: niente astrazioni o funzioni speculative.

## Accessibility & Inclusion

Nessun requisito specifico dichiarato; vale il buon senso (contrasto, testo leggibile, uso da mobile).
