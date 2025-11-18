"""Script de migration pour rendre article_id nullable dans article_images.

Ce script modifie la colonne article_id pour permettre l'upload d'images
avant la création de l'article.

Usage:
    python migrations/make_article_id_nullable.py
    ou depuis Docker:
    docker exec discord_blog_backend python migrations/make_article_id_nullable.py
"""
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import engine
from app.config import settings


def migrate():
    """Modifie la colonne article_id pour la rendre nullable.

    Returns:
        bool: True si la migration a réussi, False sinon
    """
    print("=" * 60)
    print("Migration: Rendre article_id nullable dans article_images")
    print("=" * 60)
    
    db_info = settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'local'
    print(f"Base de données: {db_info}")
    print()

    try:
        with engine.begin() as conn:  # begin() gère automatiquement le commit/rollback
            # Vérifier si la colonne existe et si elle est déjà nullable
            result = conn.execute(text("""
                SELECT is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'article_images' 
                AND column_name = 'article_id'
            """))
            
            row = result.fetchone()
            if not row:
                print("❌ La colonne article_id n'existe pas dans article_images")
                print("   La table article_images n'existe peut-être pas encore.")
                return False
            
            is_nullable = row[0]
            if is_nullable == 'YES':
                print("✅ La colonne article_id est déjà nullable")
                print("   Aucune action nécessaire.")
                return True

            # Modifier la colonne pour la rendre nullable
            print("Modification de la colonne article_id...")
            conn.execute(text("""
                ALTER TABLE article_images 
                ALTER COLUMN article_id DROP NOT NULL
            """))
            print("✅ Migration réussie: article_id est maintenant nullable")
            print()
            print("Vous pouvez maintenant uploader des images avant de créer un article.")
            return True

    except Exception as e:
        print(f"❌ Erreur lors de la migration: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)

