-- Durata delle condizioni economiche, attivazione (solo offerta attuale) e testi del venditore da mostrare.
ALTER TABLE offers ADD COLUMN duration_months INTEGER;
ALTER TABLE offers ADD COLUMN started_on TEXT;
ALTER TABLE offers ADD COLUMN conditions TEXT;
ALTER TABLE offers ADD COLUMN after_term TEXT;
