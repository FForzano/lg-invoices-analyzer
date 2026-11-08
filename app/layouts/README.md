# Layout di lettura forniti con l'app

Ogni file `*.json` qui è un layout che `services/layouts.py` carica all'avvio della lettura (dopo `bill_parser`, prima dell'LLM).
Il formato è quello esportato da «Layout di lettura → Segnala»: solo il nome del fornitore e, per ogni campo, l'etichetta accanto al valore.

Per aggiungere un fornitore da una segnalazione:

1. Controlla che il JSON non contenga dati personali (etichette tipo «Cliente Mario Rossi», codici, numeri lunghi): in tal caso togli la regola.
2. Salvalo come `app/layouts/<fornitore>.json`.
3. Scrivi un test con un estratto *anonimo* di testo (`tests/fixtures/`) che inventa i valori e verifica i campi letti (vedi `tests/test_layouts.py`).

Un file non valido viene ignorato, non blocca la lettura. Layout con una logica che le regole non esprimono (celle incollate, controlli incrociati) vanno invece in `services/bill_parser.py`.
