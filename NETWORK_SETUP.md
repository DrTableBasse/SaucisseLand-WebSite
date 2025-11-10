# Configuration réseau - Accès par IP ou nom de domaine

Ce guide explique comment configurer l'application pour qu'elle soit accessible depuis d'autres machines via une IP ou un nom de domaine.

## Configuration rapide

### 1. Trouver l'IP de votre machine

#### Sur Windows :
```powershell
ipconfig
```
Cherchez l'adresse IPv4 (ex: `192.168.1.100`)

#### Sur Linux/Mac :
```bash
ip addr show
# ou
ifconfig
```

### 2. Configurer le fichier `.env`

Modifiez votre fichier `.env` pour utiliser votre IP ou nom de domaine :

```env
# Remplacez par votre IP ou nom de domaine
BASE_URL=http://192.168.1.100:8000

# Ou avec un nom de domaine :
# BASE_URL=http://example.com

# Les autres variables restent identiques
DISCORD_CLIENT_ID=1269969019813761126
DISCORD_CLIENT_SECRET=votre_secret
DISCORD_GUILD_ID=1280110865852399687
DISCORD_BOT_TOKEN=votre_token
ALLOWED_ROLE_IDS=1280110865890410656
SECRET_KEY=votre_secret_key
```

**Note importante** : `DISCORD_REDIRECT_URI` sera automatiquement construit à partir de `BASE_URL`. Vous n'avez pas besoin de le définir manuellement.

### 3. Configurer Discord OAuth

1. Allez sur https://discord.com/developers/applications
2. Sélectionnez votre application
3. Dans **OAuth2** → **General**
4. Ajoutez l'URL de redirection avec votre IP/domaine :
   ```
   http://192.168.1.100:8000/api/auth/callback/social/discord
   ```
   (Remplacez `192.168.1.100` par votre IP ou domaine)

5. Sauvegardez

### 4. Redémarrer les services

```bash
docker-compose restart backend
```

### 5. Tester

Depuis une autre machine sur le même réseau :
- Ouvrez `http://192.168.1.100:8000` dans un navigateur
- L'application devrait être accessible

## Configuration CORS (optionnel)

Si vous voulez autoriser des origines spécifiques, vous pouvez définir `CORS_ORIGINS` :

```env
CORS_ORIGINS=http://192.168.1.100:8000,http://192.168.1.100:3000,http://localhost:8000
```

Si `CORS_ORIGINS` n'est pas défini, il utilisera automatiquement `BASE_URL`.

## Exemples de configuration

### Accès réseau local (IP)
```env
BASE_URL=http://192.168.1.100:8000
```

### Nom de domaine
```env
BASE_URL=http://blog.example.com
```

### Développement local
```env
BASE_URL=http://localhost:8000
```

### Plusieurs origines
```env
BASE_URL=http://192.168.1.100:8000
CORS_ORIGINS=http://192.168.1.100:8000,http://192.168.1.100:3000,http://localhost:8000
```

## Dépannage

### L'application n'est pas accessible depuis une autre machine

1. **Vérifiez le firewall** :
   - Windows : Autorisez le port 8000 dans le pare-feu Windows
   - Linux : `sudo ufw allow 8000`

2. **Vérifiez que Docker écoute sur toutes les interfaces** :
   - Le `docker-compose.yml` utilise déjà `--host 0.0.0.0`, ce qui est correct

3. **Vérifiez que les machines sont sur le même réseau** :
   - Les deux machines doivent être sur le même réseau local

4. **Testez la connexion** :
   ```bash
   # Depuis l'autre machine
   ping 192.168.1.100
   curl http://192.168.1.100:8000/health
   ```

### Discord OAuth ne fonctionne pas

1. Vérifiez que l'URL de redirection dans Discord correspond exactement à `BASE_URL/api/auth/callback/social/discord`
2. Vérifiez que `BASE_URL` est correct dans votre `.env`
3. Redémarrez le backend après modification

## Sécurité

⚠️ **Important pour la production** :
- Utilisez HTTPS avec un certificat SSL
- Configurez un reverse proxy (nginx, traefik, etc.)
- Ne laissez pas le port 8000 ouvert publiquement sans protection

