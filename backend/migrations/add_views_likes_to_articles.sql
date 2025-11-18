-- Migration pour ajouter les colonnes views et likes à la table articles

ALTER TABLE articles 
ADD COLUMN IF NOT EXISTS views INTEGER DEFAULT 0 NOT NULL,
ADD COLUMN IF NOT EXISTS likes INTEGER DEFAULT 0 NOT NULL;

