"""
Script pour générer une clé secrète
"""
import secrets

if __name__ == "__main__":
    secret = secrets.token_urlsafe(32)
    print(f"SECRET_KEY={secret}")

