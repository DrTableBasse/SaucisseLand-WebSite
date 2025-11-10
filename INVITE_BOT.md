# Guide : Inviter le bot Discord sur votre serveur

## Problème
Le bot n'a pas accès au serveur (Status 401). Le bot doit être invité sur le serveur Discord pour pouvoir vérifier les rôles des utilisateurs.

## Solution : Inviter le bot

### Méthode 1 : URL directe (Recommandé)

1. **Cliquez sur ce lien** (ou copiez-collez dans votre navigateur) :
   ```
   https://discord.com/api/oauth2/authorize?client_id=1269969019813761126&permissions=268435456&scope=bot
   ```

2. **Sélectionnez votre serveur Discord** (celui avec le Guild ID: `1280110865852399687`)

3. **Autorisez le bot** avec les permissions demandées

4. **Redémarrez le backend** :
   ```bash
   docker-compose restart backend
   ```

5. **Rechargez la page de debug** (`/debug`) pour vérifier que ça fonctionne

### Méthode 2 : Via Discord Developer Portal

1. Allez sur https://discord.com/developers/applications
2. Sélectionnez votre application
3. Allez dans **OAuth2** → **URL Generator**
4. Sélectionnez :
   - **Scopes** : `bot`
   - **Bot Permissions** : `Read Members` (ou toutes les permissions)
5. Copiez l'URL générée et ouvrez-la dans votre navigateur
6. Sélectionnez le serveur avec le Guild ID `1280110865852399687`
7. Autorisez le bot

## Vérifications après l'invitation

1. **Vérifier que le bot est sur le serveur** :
   - Allez sur votre serveur Discord
   - Vérifiez que le bot apparaît dans la liste des membres

2. **Activer le Server Members Intent** :
   - Discord Developer Portal → Votre application → **Bot**
   - Scroller jusqu'à **"Privileged Gateway Intents"**
   - Activer **"Server Members Intent"**
   - Sauvegarder

3. **Vérifier les permissions du bot** :
   - Sur le serveur Discord, allez dans **Paramètres du serveur** → **Rôles**
   - Trouvez le rôle du bot
   - Vérifiez qu'il a la permission **"Read Members"** ou **"View Members"**

4. **Redémarrer le backend** :
   ```bash
   docker-compose restart backend
   ```

5. **Tester** :
   - Allez sur `/debug`
   - "Accès au serveur" devrait être ✅ Oui
   - Vos rôles Discord devraient apparaître

## Permissions nécessaires

Le bot a besoin de :
- ✅ **Read Members** (pour voir les membres et leurs rôles)
- ✅ **Server Members Intent** (activé dans les paramètres du bot)

## Dépannage

Si après avoir invité le bot, vous avez toujours une erreur 401 :

1. **Vérifiez le bot token** dans le fichier `.env` :
   - Il doit correspondre au token affiché dans Discord Developer Portal → Bot
   - Si le token a été réinitialisé, mettez à jour le `.env`

2. **Vérifiez le Guild ID** :
   - Assurez-vous que `1280110865852399687` est le bon ID du serveur
   - Pour obtenir l'ID : Mode développeur activé → Clic droit sur le serveur → "Copier l'ID"

3. **Vérifiez les logs** :
   ```bash
   docker-compose logs -f backend
   ```
   Les logs vous donneront plus d'informations sur l'erreur.

