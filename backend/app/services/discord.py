"""Service pour interagir avec l'API Discord."""
import logging
from typing import Dict, List, Optional

import aiohttp

from app.config import settings

logger = logging.getLogger(__name__)


class DiscordService:
    """Service pour les interactions avec Discord API."""

    def __init__(self):
        """Initialise le service Discord avec les credentials."""
        self.client_id = settings.DISCORD_CLIENT_ID
        self.client_secret = settings.DISCORD_CLIENT_SECRET
        # Utiliser DISCORD_REDIRECT_URI si défini, sinon construire depuis BASE_URL
        if settings.DISCORD_REDIRECT_URI:
            self.redirect_uri = settings.DISCORD_REDIRECT_URI
        else:
            # Construire le redirect URI depuis BASE_URL pour que tous les utilisateurs pointent vers le serveur
            base_url = settings.BASE_URL.rstrip("/")
            self.redirect_uri = f"{base_url}/api/auth/callback/social/discord"
        self.bot_token = settings.DISCORD_BOT_TOKEN
        self.guild_id = settings.DISCORD_GUILD_ID
        self.api_base = "https://discord.com/api/v10"
    
    async def exchange_code_for_token(self, code: str) -> Dict:
        """Échange le code OAuth contre un token d'accès.

        Args:
            code: Code d'autorisation retourné par Discord

        Returns:
            Dict: Dictionnaire contenant le token d'accès et autres infos

        Raises:
            ValueError: Si l'échange échoue
        """
        async with aiohttp.ClientSession() as session:
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
            }
            logger.info(
                f"Échange du code OAuth avec redirect_uri: {self.redirect_uri}"
            )
            logger.info(
                f"Client ID: {self.client_id[:10]}..., "
                f"Redirect URI: {self.redirect_uri}"
            )
            async with session.post(
                f"{self.api_base}/oauth2/token",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ) as response:
                response_data = await response.json()
                if response.status != 200:
                    error_msg = response_data.get(
                        "error_description",
                        response_data.get("error", "Unknown error"),
                    )
                    logger.error(
                        f"Erreur lors de l'échange du code OAuth: {error_msg} "
                        f"(status: {response.status})"
                    )
                    raise ValueError(f"Discord OAuth error: {error_msg}")
                return response_data
    
    async def get_user_info(self, access_token: str) -> Dict:
        """Récupère les informations de l'utilisateur Discord.

        Args:
            access_token: Token d'accès OAuth

        Returns:
            Dict: Informations de l'utilisateur Discord

        Raises:
            ValueError: Si la récupération échoue
        """
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {access_token}"}
            async with session.get(
                f"{self.api_base}/users/@me", headers=headers
            ) as response:
                response_data = await response.json()
                if response.status != 200:
                    error_msg = response_data.get(
                        "message", response_data.get("error", "Unknown error")
                    )
                    logger.error(
                        f"Erreur lors de la récupération des infos utilisateur: "
                        f"{error_msg} (status: {response.status})"
                    )
                    raise ValueError(f"Discord API error: {error_msg}")
                return response_data
    
    async def get_user_guild_member(self, user_id: str) -> Optional[Dict]:
        """Récupère les informations du membre dans le serveur Discord.

        Args:
            user_id: ID Discord de l'utilisateur

        Returns:
            Optional[Dict]: Informations du membre ou None si non trouvé
        """
        
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
        """Récupère la liste des rôles de l'utilisateur.

        Args:
            user_id: ID Discord de l'utilisateur

        Returns:
            List[str]: Liste des IDs de rôles de l'utilisateur
        """
        
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
    
    async def search_users_by_username(self, query: str, limit: int = 10) -> List[Dict]:
        """Recherche des utilisateurs par pseudo avec autocomplétion.
        
        Cette méthode utilise la table user_voice_data pour rechercher les utilisateurs,
        ce qui évite la limite de 1000 membres de l'API Discord.
        
        Args:
            query: Terme de recherche (pseudo Discord)
            limit: Nombre maximum de résultats à retourner
        
        Returns:
            List[Dict]: Liste des utilisateurs trouvés avec leurs informations
        """
        from app.database import SessionLocal
        from sqlalchemy import text
        import aiohttp
        
        # Nettoyer le terme de recherche
        query_clean = query.strip().lower()
        
        if not query_clean or len(query_clean) < 2:
            return []
        
        try:
            db = SessionLocal()
            try:
                # Rechercher dans la base de données par username ou nickname avec JOIN sur users pour récupérer l'avatar
                sql_query = text("""
                    SELECT 
                        uvd.user_id, 
                        uvd.username, 
                        uvd.nickname,
                        u.avatar
                    FROM user_voice_data uvd
                    LEFT JOIN users u ON u.discord_id = CAST(uvd.user_id AS TEXT)
                    WHERE LOWER(uvd.username) LIKE :search_like
                       OR LOWER(uvd.nickname) LIKE :search_like
                    ORDER BY 
                        CASE 
                            WHEN LOWER(uvd.username) = :search THEN 1
                            WHEN LOWER(uvd.nickname) = :search THEN 2
                            WHEN LOWER(uvd.username) LIKE :search_exact THEN 3
                            WHEN LOWER(uvd.nickname) LIKE :search_exact THEN 4
                            WHEN LOWER(uvd.username) LIKE :search_like THEN 5
                            WHEN LOWER(uvd.nickname) LIKE :search_like THEN 6
                        END
                    LIMIT :limit
                """)
                
                result = db.execute(sql_query, {
                    "search": query_clean,
                    "search_exact": f"{query_clean}%",
                    "search_like": f"%{query_clean}%",
                    "limit": limit
                })
                rows = result.fetchall()
                
                users = []
                
                for row in rows:
                    user_id, db_username, db_nickname, avatar_hash = row
                    # S'assurer que user_id est converti en string de manière sûre
                    # user_id peut être un int, un str, ou un Decimal depuis PostgreSQL
                    if isinstance(user_id, (int, float)):
                        user_id_str = str(int(user_id))
                    else:
                        user_id_str = str(user_id)
                    
                    logger.info(f"🔍 DEBUG search_users_by_username: user_id brut={user_id} (type: {type(user_id)}), user_id_str={user_id_str}, username={db_username}")
                    
                    # Construire l'URL de l'avatar depuis la base de données
                    if avatar_hash:
                        avatar_url = f"https://cdn.discordapp.com/avatars/{user_id_str}/{avatar_hash}.png?size=64"
                    else:
                        # Avatar par défaut Discord basé sur l'ID
                        avatar_url = f"https://cdn.discordapp.com/embed/avatars/{int(user_id_str) % 5}.png"
                    
                    users.append({
                        "id": user_id_str,
                        "username": db_username,
                        "nickname": db_nickname if db_nickname and db_nickname != db_username else None,
                        "display_name": db_nickname if db_nickname else db_username,
                        "avatar_url": avatar_url
                    })
                    
                    logger.info(f"🔍 DEBUG search_users_by_username: Utilisateur ajouté avec id={user_id_str}")
                
                return users
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Erreur lors de la recherche d'utilisateurs: {e}")
            return []
    
    async def find_user_by_username(self, username: str) -> Optional[Dict]:
        """Recherche un utilisateur par son pseudo dans la base de données.
        
        Cette méthode utilise la table user_voice_data pour rechercher les utilisateurs,
        ce qui évite la limite de 1000 membres de l'API Discord.
        
        Args:
            username: Pseudo Discord de l'utilisateur (ex: "ricardomilos__")
        
        Returns:
            Optional[Dict]: Informations du membre trouvé ou None si non trouvé
        """
        from app.database import SessionLocal
        from sqlalchemy import text
        
        # Nettoyer le pseudo (enlever les espaces, etc.)
        username_clean = username.strip().lower()
        
        try:
            db = SessionLocal()
            try:
                # Rechercher dans la base de données par username ou nickname
                query = text("""
                    SELECT user_id, username, nickname 
                    FROM user_voice_data 
                    WHERE LOWER(username) = :search 
                       OR LOWER(nickname) = :search
                       OR LOWER(username) LIKE :search_like
                       OR LOWER(nickname) LIKE :search_like
                    ORDER BY 
                        CASE 
                            WHEN LOWER(username) = :search THEN 1
                            WHEN LOWER(nickname) = :search THEN 2
                            WHEN LOWER(username) LIKE :search_like THEN 3
                            WHEN LOWER(nickname) LIKE :search_like THEN 4
                        END
                    LIMIT 1
                """)
                
                result = db.execute(query, {
                    "search": username_clean,
                    "search_like": f"{username_clean}%"
                })
                row = result.fetchone()
                
                if row:
                    user_id, db_username, db_nickname = row
                    
                    # Construire un dictionnaire similaire à ce que l'API Discord retournerait
                    found_member = {
                        "user": {
                            "id": str(user_id),
                            "username": db_username,
                            "discriminator": "0",  # Discord a supprimé les discriminators
                            "global_name": db_nickname if db_nickname else None
                        },
                        "nick": db_nickname if db_nickname and db_nickname != db_username else None,
                        "roles": []  # Les rôles ne sont pas stockés dans user_voice_data
                    }
                    
                    logger.info(f"Utilisateur trouvé dans la BDD: {db_username} ({user_id})")
                    return found_member
                else:
                    logger.debug(f"Aucun utilisateur trouvé pour '{username}' dans la BDD")
                    return None
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Erreur lors de la recherche d'utilisateur dans la BDD: {e}")
            # Fallback vers l'API Discord en cas d'erreur BDD
            logger.warning("Tentative de recherche via l'API Discord en fallback...")
            return await self._find_user_by_username_api_fallback(username)
    
    async def _find_user_by_username_api_fallback(self, username: str) -> Optional[Dict]:
        """Fallback vers l'API Discord si la recherche BDD échoue."""
        username_clean = username.strip().lower()
        
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bot {self.bot_token}"}
            url = f"{self.api_base}/guilds/{self.guild_id}/members"
            params = {"limit": 1000}
            found_member = None
            
            try:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        members = await response.json()
                        
                        for member in members:
                            user_info = member.get("user", {})
                            member_username = user_info.get("username", "").lower()
                            member_nick = member.get("nick", "").lower() if member.get("nick") else ""
                            
                            if member_username == username_clean or member_nick == username_clean:
                                found_member = member
                                break
                        
                        if not found_member:
                            for member in members:
                                user_info = member.get("user", {})
                                member_username = user_info.get("username", "").lower()
                                member_nick = member.get("nick", "").lower() if member.get("nick") else ""
                                
                                if (member_username.startswith(username_clean) or
                                    member_nick.startswith(username_clean)):
                                    found_member = member
                                    break
                    
                    elif response.status == 403:
                        logger.error("Le bot n'a pas les permissions pour lister les membres")
                    elif response.status == 404:
                        logger.warning(f"Serveur {self.guild_id} non trouvé")
            
            except Exception as e:
                logger.error(f"Erreur lors de la recherche d'utilisateur (fallback API): {e}")
            
            return found_member
    
    async def check_user_has_allowed_role(self, user_id: str) -> bool:
        """Vérifie si l'utilisateur a un des rôles autorisés.

        Args:
            user_id: ID Discord de l'utilisateur

        Returns:
            bool: True si l'utilisateur a un rôle autorisé, False sinon
        """
        
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

