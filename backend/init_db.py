"""
Script pour initialiser la base de données
"""
from app.database import engine, Base
from app.models import User, Article, ArticleImage, ArticleLike

if __name__ == "__main__":
    print("Création des tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables créées avec succès!")

