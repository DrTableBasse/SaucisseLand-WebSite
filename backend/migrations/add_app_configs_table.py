"""Migration: Créer la table app_configs pour les configurations dynamiques."""
import sys
import os

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine

def run_migration():
    """Exécute la migration pour créer la table app_configs."""
    migration_sql = """
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
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(text(migration_sql))
            conn.commit()
            print("✅ Migration réussie: Table app_configs créée avec succès")
    except Exception as e:
        print(f"❌ Erreur lors de la migration: {e}")
        raise

if __name__ == "__main__":
    run_migration()
