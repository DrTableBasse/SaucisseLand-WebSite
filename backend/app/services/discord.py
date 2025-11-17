import aiohttp
from typing import Optional, List, Dict
from app.config import settings

class DiscordService:
    def __init__(self):
        self.client_id = settings.DISCORD_CLIENT_ID
        self.client_secret = settings.DISCORD_CLIENT_SECRET
        self.redirect_uri = settings.DISCORD_REDIRECT_URI_FINAL
        self.bot_token = settings.DISCORD_BOT_TOKEN
        self.guild_id = settings.DISCORD_GUILD_ID
        self.api_base = "https://discord.com/api/v10"
    
    async def exchange_code_for_token(self, code: str) -> Dict:
        """Échange le code OAuth contre un token d'accès"""
        import logging
        logger = logging.getLogger(__name__)
        
        async with aiohttp.ClientSession() as session:
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
            }
            logger.debug(f"Échange du code OAuth avec redirect_uri: {self.redirect_uri}")
            
            async with session.post(
                f"{self.api_base}/oauth2/token",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            ) as response:
                result = await response.json()
                if response.status != 200:
                    error_msg = result.get("error_description", result.get("error", "Unknown error"))
                    logger.error(f"Erreur lors de l'échange du token (status {response.status}): {error_msg}")
                    logger.error(f"Redirect URI utilisé: {self.redirect_uri}")
                return result
    
    async def get_user_info(self, access_token: str) -> Dict:
        """Récupère les informations de l'utilisateur Discord"""
        import logging
        logger = logging.getLogger(__name__)
        
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {access_token}"}
            async with session.get(
                f"{self.api_base}/users/@me",
                headers=headers
            ) as response:
                result = await response.json()
                if response.status != 200:
                    error_msg = result.get("message", "Unknown error")
                    logger.error(f"Erreur lors de la récupération des infos utilisateur (status {response.status}): {error_msg}")
                return result
    
    async def get_user_guild_member(self, user_id: str) -> Optional[Dict]:
        """Récupère les informations du membre dans le serveur Discord"""
        import logging
        logger = logging.getLogger(__name__)
        
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bot {self.bot_token}"}
            url = f"{self.api_base}/guilds/{self.guild_id}/members/{user_id}"
            logger.info(f"Tentative de récupération du membre {user_id} depuis {url}")
            
            async with session.get(url, headers=headers) as response:
                logger.info(f"Réponse Discord API: status={response.status}")
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Données du membre récupérées: {data}")
                    return data
                elif response.status == 404:
                    logger.warning(f"Utilisateur {user_id} non trouvé sur le serveur {self.guild_id}")
                    # Essayer de récupérer les infos du serveur pour vérifier
                    try:
                        async with session.get(
                            f"{self.api_base}/guilds/{self.guild_id}",
                            headers=headers
                        ) as guild_response:
                            if guild_response.status == 200:
                                logger.info("Le serveur existe et le bot y a accès")
                            else:
                                logger.error(f"Le bot n'a pas accès au serveur: {guild_response.status}")
                    except Exception as e:
                        logger.error(f"Erreur lors de la vérification du serveur: {e}")
                else:
                    error_text = await response.text()
                    logger.error(f"Erreur API Discord (status {response.status}): {error_text}")
                return None
    
    async def get_user_roles(self, user_id: str) -> List[str]:
        """Récupère la liste des rôles de l'utilisateur"""
        import logging
        logger = logging.getLogger(__name__)
        
        member = await self.get_user_guild_member(user_id)
        if not member:
            logger.warning(f"Aucun membre trouvé pour {user_id}")
            return []
        
        roles = member.get("roles", [])
        # S'assurer que tous les rôles sont des strings
        roles = [str(role) for role in roles]
        logger.info(f"Rôles trouvés pour {user_id} (type: {type(roles)}): {roles}")
        logger.info(f"Types individuels: {[type(r).__name__ for r in roles]}")
        return roles
    
    async def check_user_has_allowed_role(self, user_id: str) -> bool:
        """Vérifie si l'utilisateur a un des rôles autorisés"""
        import logging
        logger = logging.getLogger(__name__)
        
        member = await self.get_user_guild_member(user_id)
        if not member:
            logger.warning(f"Utilisateur {user_id} non trouvé dans le serveur Discord")
            return False
        
        user_roles = member.get("roles", [])
        # S'assurer que tous les rôles sont des strings
        user_roles = [str(role) for role in user_roles]
        allowed_roles = settings.ALLOWED_ROLE_IDS
        # S'assurer que tous les rôles autorisés sont des strings
        allowed_roles = [str(role).strip() for role in allowed_roles]
        
        logger.info(f"Rôles de l'utilisateur {user_id} (type: {type(user_roles)}): {user_roles}")
        logger.info(f"Rôles autorisés (type: {type(allowed_roles)}): {allowed_roles}")
        logger.info(f"Types des rôles utilisateur: {[type(r).__name__ for r in user_roles]}")
        logger.info(f"Types des rôles autorisés: {[type(r).__name__ for r in allowed_roles]}")
        
        # Vérifier si l'utilisateur a au moins un des rôles autorisés
        has_permission = any(str(role_id).strip() in user_roles for role_id in allowed_roles)
        
        # Debug détaillé
        if not has_permission and allowed_roles:
            logger.warning(f"Comparaison détaillée:")
            for allowed_role in allowed_roles:
                found = str(allowed_role).strip() in user_roles
                logger.warning(f"  - Rôle autorisé '{allowed_role}' (type: {type(allowed_role).__name__}) dans les rôles utilisateur: {found}")
                if not found:
                    # Chercher des correspondances partielles
                    similar = [r for r in user_roles if str(allowed_role).strip() in str(r) or str(r) in str(allowed_role).strip()]
                    if similar:
                        logger.warning(f"    Rôles similaires trouvés: {similar}")
        
        logger.info(f"L'utilisateur {user_id} a les permissions: {has_permission}")
        
        return has_permission

discord_service = DiscordService()

