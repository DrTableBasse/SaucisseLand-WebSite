# Discord Blog - FastAPI

Application web de blog avec authentification Discord, gestion d'articles en Markdown et vérification des rôles Discord.

## Fonctionnalités

- 🔐 **Authentification Discord** : Connexion via OAuth2 Discord
- 📝 **Articles Markdown** : Création et gestion d'articles en Markdown
- 🖼️ **Upload d'images** : Stockage et gestion des images pour les articles
- 🛡️ **Vérification des rôles** : Seuls les utilisateurs avec des rôles Discord spécifiques peuvent créer des articles
- 🐳 **Conteneurisation** : Backend et base de données conteneurisés avec Docker
- 🗄️ **PostgreSQL** : Base de données PostgreSQL avec SQLAlchemy

## Prérequis

- Docker et Docker Compose
- Un bot Discord avec les permissions nécessaires
- Un compte Discord Developer pour obtenir les credentials OAuth

## Configuration

1. **Cloner le projet** (ou utiliser le projet existant)

2. **Créer un fichier `.env`** à la racine du projet :

```env
# Base URL (IP, nom de domaine ou localhost)
# Pour accès réseau local: http://192.168.1.100:8000
# Pour nom de domaine: http://example.com
# Pour développement local: http://localhost:8000
BASE_URL=http://localhost:8000

# Database
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=discord_blog

# Discord OAuth
DISCORD_CLIENT_ID=votre_client_id
DISCORD_CLIENT_SECRET=votre_client_secret
# DISCORD_REDIRECT_URI sera construit automatiquement à partir de BASE_URL
DISCORD_GUILD_ID=1280110865852399687
DISCORD_BOT_TOKEN=votre_bot_token

# Allowed role IDs (séparés par des virgules)
# Exemple: ALLOWED_ROLE_IDS=123456789012345678,987654321098765432
ALLOWED_ROLE_IDS=

# Secret key for sessions (générer avec: python -c "import secrets; print(secrets.token_urlsafe(32))")
SECRET_KEY=votre_secret_key_ici

# CORS Origins (optionnel - utilise BASE_URL par défaut)
# Exemple: CORS_ORIGINS=http://192.168.1.100:8000,http://localhost:8000
```

3. **Configurer Discord OAuth** :
   - Aller sur le [Discord Developer Portal](https://discord.com/developers/applications)
   - Créer une nouvelle application ou utiliser une existante
   - Dans "OAuth2", ajouter le redirect URI : `{BASE_URL}/api/auth/callback/social/discord`
     - Exemple avec IP : `http://192.168.1.100:8000/api/auth/callback/social/discord`
     - Exemple avec localhost : `http://localhost:8000/api/auth/callback/social/discord`
   - Copier le Client ID et Client Secret dans le `.env`
   - Créer un bot et copier le token dans `DISCORD_BOT_TOKEN`

4. **Configurer les rôles autorisés** :
   - Obtenir les IDs des rôles Discord autorisés à créer des articles
   - Les ajouter dans `ALLOWED_ROLE_IDS` séparés par des virgules

## Installation et démarrage

### Avec Docker Compose (recommandé)

```bash
# Démarrer tous les services
docker-compose up -d

# Voir les logs
docker-compose logs -f

# Arrêter les services
docker-compose down
```

L'application sera accessible sur l'URL définie dans `BASE_URL` (par défaut `http://localhost:8000`)

**Pour accès réseau local** : Configurez `BASE_URL` avec votre IP (ex: `http://192.168.1.100:8000`) et ajoutez cette URL dans Discord OAuth. Voir `NETWORK_SETUP.md` pour plus de détails.

### Développement local (sans Docker)

1. **Installer PostgreSQL** et créer une base de données

2. **Installer les dépendances Python** :
```bash
cd backend
pip install -r requirements.txt
```

3. **Configurer la base de données** :
```bash
# Créer les migrations
alembic revision --autogenerate -m "Initial migration"

# Appliquer les migrations
alembic upgrade head
```

4. **Démarrer le serveur** :
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Structure du projet

```
.
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # Point d'entrée FastAPI
│   │   ├── config.py             # Configuration
│   │   ├── database.py           # Configuration SQLAlchemy
│   │   ├── models.py             # Modèles de base de données
│   │   ├── schemas.py            # Schémas Pydantic
│   │   ├── routers/              # Routes API
│   │   │   ├── auth.py           # Authentification
│   │   │   ├── articles.py       # Gestion des articles
│   │   │   └── images.py         # Upload d'images
│   │   └── services/
│   │       └── discord.py        # Service Discord API
│   ├── templates/                # Templates Jinja2
│   ├── static/                   # Fichiers statiques
│   ├── uploads/                  # Images uploadées
│   ├── alembic/                  # Migrations
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml
└── .env
```

## API Endpoints

### Authentification
- `GET /api/auth/login` - Redirige vers Discord OAuth
- `GET /api/auth/callback` - Callback OAuth
- `POST /api/auth/logout` - Déconnexion
- `GET /api/auth/me` - Informations utilisateur actuel

### Articles
- `GET /api/articles/` - Liste des articles
- `GET /api/articles/{slug}` - Détails d'un article
- `POST /api/articles/` - Créer un article (nécessite un rôle autorisé)
- `PUT /api/articles/{id}` - Modifier un article
- `DELETE /api/articles/{id}` - Supprimer un article

### Images
- `POST /api/images/upload` - Upload une image
- `GET /api/images/{id}` - Informations d'une image
- `GET /api/images/article/{article_id}` - Images d'un article
- `DELETE /api/images/{id}` - Supprimer une image

## Utilisation

1. **Se connecter** : Cliquer sur "Connexion Discord" et autoriser l'application
2. **Créer un article** : Seuls les utilisateurs avec les rôles autorisés peuvent créer des articles
3. **Upload d'images** : Lors de la création d'un article, utiliser la section "Upload d'images"
4. **Publier** : Cocher "Publier immédiatement" pour rendre l'article visible

## Notes importantes

- Le token du bot Discord doit avoir les permissions `bot` et `guilds.members.read`
- Le bot doit être présent sur le serveur Discord avec le Guild ID spécifié
- Les rôles autorisés doivent être configurés dans `ALLOWED_ROLE_IDS`
- Les images sont stockées dans `backend/uploads/` (créer le dossier si nécessaire)

## Développement

Pour le développement avec hot-reload :

```bash
docker-compose up
```

Le backend se rechargera automatiquement grâce à `--reload` dans la commande uvicorn.

## Licence

MIT
