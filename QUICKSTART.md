# Guide de démarrage rapide

## 1. Configuration Discord

### Créer une application Discord

1. Aller sur https://discord.com/developers/applications
2. Créer une nouvelle application
3. Dans "OAuth2" → "General" :
   - Copier le **Client ID**
   - Créer un **Client Secret** et le copier
   - Ajouter un Redirect URI : `http://localhost:8000/api/auth/callback`

### Créer un bot

1. Dans "Bot" :
   - Créer un bot
   - Copier le **Token**
   - Activer les intents suivants :
     - Server Members Intent (nécessaire pour vérifier les rôles)

### Inviter le bot sur votre serveur

1. Dans "OAuth2" → "URL Generator" :
   - Scopes : `bot`, `guilds.members.read`
   - Bot Permissions : `Read Members`
   - Copier l'URL générée et l'ouvrir dans un navigateur
   - Sélectionner votre serveur (Guild ID: 1280110865852399687)

### Obtenir les IDs des rôles

1. Activer le mode développeur dans Discord (Paramètres → Avancé → Mode développeur)
2. Clic droit sur un rôle → Copier l'ID
3. Répéter pour tous les rôles autorisés à créer des articles

## 2. Configuration du projet

1. **Créer le fichier `.env`** à partir de `.env.example` :

```bash
cp .env.example .env
```

2. **Remplir le fichier `.env`** avec vos valeurs :

```env
# Database (par défaut, OK pour le développement)
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=discord_blog

# Discord OAuth (remplacer avec vos valeurs)
DISCORD_CLIENT_ID=votre_client_id_ici
DISCORD_CLIENT_SECRET=votre_client_secret_ici
DISCORD_REDIRECT_URI=http://localhost:8000/api/auth/callback
DISCORD_GUILD_ID=1280110865852399687
DISCORD_BOT_TOKEN=votre_bot_token_ici

# Rôles autorisés (IDs séparés par des virgules)
ALLOWED_ROLE_IDS=123456789012345678,987654321098765432

# Générer une clé secrète
SECRET_KEY=$(python backend/generate_secret.py | cut -d= -f2)

# CORS
CORS_ORIGINS=http://localhost:8000,http://localhost:3000
```

3. **Générer une clé secrète** :

```bash
cd backend
python generate_secret.py
```

Copier la sortie dans `SECRET_KEY` du fichier `.env`.

## 3. Démarrer l'application

### Avec Docker Compose (recommandé)

```bash
# Démarrer tous les services
docker-compose up -d

# Voir les logs
docker-compose logs -f backend

# Arrêter
docker-compose down
```

L'application sera accessible sur http://localhost:8000

### Sans Docker

1. **Installer PostgreSQL** et créer une base de données
2. **Installer les dépendances** :

```bash
cd backend
pip install -r requirements.txt
```

3. **Initialiser la base de données** :

```bash
python init_db.py
```

4. **Démarrer le serveur** :

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 4. Utilisation

1. Ouvrir http://localhost:8000
2. Cliquer sur "Connexion Discord"
3. Autoriser l'application
4. Si vous avez un des rôles autorisés, vous pourrez créer des articles
5. Sinon, vous verrez un message d'erreur lors de la création

## Dépannage

### Le bot ne peut pas vérifier les rôles

- Vérifier que le bot est bien sur le serveur
- Vérifier que les intents sont activés (Server Members Intent)
- Vérifier que le bot a les permissions nécessaires

### Erreur de connexion à la base de données

- Vérifier que PostgreSQL est démarré
- Vérifier les credentials dans `.env`
- Vérifier que la base de données existe

### Erreur OAuth

- Vérifier que le Redirect URI est correct dans Discord Developer Portal
- Vérifier que le Client ID et Secret sont corrects

