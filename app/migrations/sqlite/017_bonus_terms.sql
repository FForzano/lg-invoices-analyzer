-- Bonus e sconti dichiarati dal venditore sul Portale Offerte ARERA (testo, una voce per riga; solo da mostrare, fuori dalla stima).
ALTER TABLE offers ADD COLUMN bonus_terms TEXT;
