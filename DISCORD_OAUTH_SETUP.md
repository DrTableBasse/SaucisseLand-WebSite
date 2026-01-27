# Configuration Discord OAuth pour accès réseau

## Problème

Par défaut, l'authentification Discord redirige vers `localhost`, ce qui fait que chaque utilisateur est redirigé vers sa propre machine au lieu du serveur.

## Solution

Le code utilise maintenant `BASE_URL` pour construire automatiquement le redirect URI. Vous devez configurer Discord pour accepter cette URL.

## Étapes de configuration

### 1. Déterminer votre URL de serveur

Vérifiez votre `BASE_URL` dans le fichier `.env` :
```env
BASE_URL=http://192.168.1.100:8000
```

L'URL de redirection sera automatiquement : `http://192.168.1.100:8000/api/auth/callback/social/discord`

### 2. Configurer Discord Developer Portal

1. **Aller sur** https://discord.com/developers/applications
2. **Sélectionner votre application** (celle utilisée pour le site)
3. **Aller dans "OAuth2" → "General"**
4. **Dans la section "Redirects"**, cliquer sur **"Add Redirect"**
5. **Ajouter l'URL de redirection** :
   - Si votre `BASE_URL` est `http://192.168.1.100:8000`
   - Ajoutez : `http://192.168.1.100:8000/api/auth/callback/social/discord`
6. **Sauvegarder les changements**

### 3. Si vous utilisez plusieurs URLs (développement + production)

Vous pouvez ajouter plusieurs redirect URIs dans Discord :
- `http://localhost:8000/api/auth/callback/social/discord` (pour développement local)
- `http://192.168.1.100:8000/api/auth/callback/social/discord` (pour accès réseau)
- `https://votre-domaine.com/api/auth/callback/social/discord` (pour production)

### 4. Vérifier la configuration

1. **Vérifier que `BASE_URL` est correct** dans votre `.env`
2. **Redémarrer le serveur backend** pour appliquer les changements
3. **Tester l'authentification** depuis une autre machine sur le réseau

## Dépannage

### Erreur "Invalid redirect_uri"

- Vérifiez que l'URL dans Discord correspond **exactement** à celle utilisée par le code
- L'URL doit être identique (pas de slash final, même protocole http/https)
- Vérifiez les logs du serveur pour voir quelle URL est utilisée

### Redirection vers localhost

- Vérifiez que `BASE_URL` est défini dans votre `.env`
- Vérifiez que `BASE_URL` n'est pas `http://localhost:8000` (utilisez votre IP réseau)
- Redémarrez le serveur après modification du `.env`

### Comment trouver votre IP réseau

**Windows :**
```powershell
ipconfig
```
Cherchez "IPv4 Address" sous votre carte réseau active.

**Linux/Mac :**
```bash
ip addr show
# ou
ifconfig
```

**Exemple :** Si votre IP est `192.168.1.100`, utilisez :
```env
BASE_URL=http://192.168.1.100:8000
```

## Notes importantes

- **Ne partagez jamais** votre `DISCORD_CLIENT_SECRET` ou `DISCORD_BOT_TOKEN`
- Les redirect URIs dans Discord sont sensibles à la casse et doivent correspondre exactement
- Si vous changez `BASE_URL`, vous devez mettre à jour les redirect URIs dans Discord
- Pour la production, utilisez HTTPS et un nom de domaine

