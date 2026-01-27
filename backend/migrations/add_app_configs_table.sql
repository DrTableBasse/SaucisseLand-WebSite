-- Migration: Créer la table app_configs pour les configurations dynamiques
-- Date: 2026-01-27

CREATE TABLE IF NOT EXISTS app_configs (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    description TEXT,
    category VARCHAR(50) DEFAULT 'general',
    is_sensitive BOOLEAN DEFAULT FALSE,
    updated_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_app_configs_key ON app_configs(key);
CREATE INDEX IF NOT EXISTS idx_app_configs_category ON app_configs(category);

-- Commentaires pour la documentation
COMMENT ON TABLE app_configs IS 'Table pour stocker les configurations dynamiques de l''application';
COMMENT ON COLUMN app_configs.key IS 'Clé unique de la configuration';
COMMENT ON COLUMN app_configs.value IS 'Valeur de la configuration';
COMMENT ON COLUMN app_configs.description IS 'Description de la configuration';
COMMENT ON COLUMN app_configs.category IS 'Catégorie de la configuration (general, metrics, security, etc.)';
COMMENT ON COLUMN app_configs.is_sensitive IS 'Si true, la valeur sera masquée dans l''interface';
COMMENT ON COLUMN app_configs.updated_by IS 'ID de l''utilisateur qui a effectué la dernière mise à jour';
