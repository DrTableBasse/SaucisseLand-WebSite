"""Script de migration pour créer la table article_likes.

Usage:
    python migrations/add_article_likes_table.py
    ou depuis Docker:
    docker exec discord_blog_backend python migrations/add_article_likes_table.py
"""
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import engine
from app.config import settings


def migrate():
    """Crée la table article_likes si elle n'existe pas.

    Returns:
        bool: True si la migration a réussi, False sinon
    """
    print("=" * 60)
    print("Migration: Créer la table article_likes")
    print("=" * 60)

    db_info = settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'local'
    print(f"Base de données: {db_info}")
    print()

    try:
        with engine.begin() as conn:
            # Vérifier si la table existe déjà
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'article_likes'
                )
            """))
            
            table_exists = result.scalar()
            
            if table_exists:
                print("✅ La table article_likes existe déjà")
                print("   Aucune action nécessaire.")
                return True

            # Créer la table
            print("Création de la table article_likes...")
            conn.execute(text("""
                CREATE TABLE article_likes (
                    id SERIAL PRIMARY KEY,
                    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(article_id, user_id)
                )
            """))
            
            # Créer les index
            print("Création des index...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_article_likes_article_id 
                ON article_likes(article_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_article_likes_user_id 
                ON article_likes(user_id)
            """))
            
            print("✅ Migration réussie: table article_likes créée")
            print()
            print("Les likes sont maintenant uniques par utilisateur.")
            return True

    except Exception as e:
        print(f"❌ Erreur lors de la migration: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)

