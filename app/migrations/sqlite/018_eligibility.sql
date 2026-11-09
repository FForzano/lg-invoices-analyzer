-- Requisiti e dettagli dell'offerta dal Portale Offerte ARERA (residenza, intervalli di potenza e consumo,
-- pagamenti, canale di attivazione, telefono) e residenza del profilo.
ALTER TABLE offers ADD COLUMN residency TEXT;
ALTER TABLE offers ADD COLUMN power_min REAL;
ALTER TABLE offers ADD COLUMN power_max REAL;
ALTER TABLE offers ADD COLUMN consumption_min REAL;
ALTER TABLE offers ADD COLUMN consumption_max REAL;
ALTER TABLE offers ADD COLUMN payment_methods TEXT;
ALTER TABLE offers ADD COLUMN activation_terms TEXT;
ALTER TABLE offers ADD COLUMN phone TEXT;
ALTER TABLE profiles ADD COLUMN resident INTEGER NOT NULL DEFAULT 1;
