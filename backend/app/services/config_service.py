"""Service de gestion des configurations dynamiques."""
import logging
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.models import AppConfig, User

logger = logging.getLogger(__name__)


class ConfigService:
    """Service pour gérer les configurations dynamiques."""

    def __init__(self):
        """Initialise le service avec un cache des configurations."""
        self._cache: Dict[str, str] = {}
        self._cache_loaded = False

    def get_config(self, db: Session, key: str, default: Optional[str] = None) -> Optional[str]:
        """Récupère une configuration depuis la base de données ou le cache.

        Args:
            db: Session de base de données
            key: Clé de la configuration
            default: Valeur par défaut si la configuration n'existe pas

        Returns:
            str ou None: Valeur de la configuration ou valeur par défaut
        """
        # Vérifier le cache d'abord
        if key in self._cache:
            return self._cache[key]

        # Charger depuis la base de données
        config = db.query(AppConfig).filter(AppConfig.key == key).first()
        if config:
            self._cache[key] = config.value
            return config.value

        return default

    def set_config(
        self,
        db: Session,
        key: str,
        value: str,
        description: Optional[str] = None,
        category: str = "general",
        is_sensitive: bool = False,
        updated_by: Optional[int] = None,
    ) -> AppConfig:
        """Définit ou met à jour une configuration.

        Args:
            db: Session de base de données
            key: Clé de la configuration
            value: Valeur de la configuration
            description: Description de la configuration
            category: Catégorie de la configuration
            is_sensitive: Si True, la valeur sera masquée dans l'interface
            updated_by: ID de l'utilisateur qui a effectué la mise à jour

        Returns:
            AppConfig: Configuration créée ou mise à jour
        """
        config = db.query(AppConfig).filter(AppConfig.key == key).first()

        if config:
            # Mise à jour
            config.value = value
            if description is not None:
                config.description = description
            if category is not None:
                config.category = category
            if is_sensitive is not None:
                config.is_sensitive = is_sensitive
            if updated_by is not None:
                config.updated_by = updated_by
        else:
            # Création
            config = AppConfig(
                key=key,
                value=value,
                description=description,
                category=category,
                is_sensitive=is_sensitive,
                updated_by=updated_by,
            )
            db.add(config)

        db.commit()
        db.refresh(config)

        # Mettre à jour le cache
        self._cache[key] = value

        logger.info(f"Configuration '{key}' mise à jour")
        return config

    def delete_config(self, db: Session, key: str) -> bool:
        """Supprime une configuration.

        Args:
            db: Session de base de données
            key: Clé de la configuration à supprimer

        Returns:
            bool: True si la configuration a été supprimée, False sinon
        """
        config = db.query(AppConfig).filter(AppConfig.key == key).first()
        if config:
            db.delete(config)
            db.commit()
            # Retirer du cache
            if key in self._cache:
                del self._cache[key]
            logger.info(f"Configuration '{key}' supprimée")
            return True
        return False

    def get_all_configs(self, db: Session) -> list[AppConfig]:
        """Récupère toutes les configurations.

        Args:
            db: Session de base de données

        Returns:
            list[AppConfig]: Liste de toutes les configurations
        """
        return db.query(AppConfig).all()

    def reload_cache(self, db: Session):
        """Recharge le cache depuis la base de données.

        Args:
            db: Session de base de données
        """
        configs = db.query(AppConfig).all()
        self._cache = {config.key: config.value for config in configs}
        self._cache_loaded = True
        logger.info(f"Cache des configurations rechargé ({len(self._cache)} configurations)")

    def is_metrics_enabled(self, db: Session) -> bool:
        """Vérifie si les métriques sont activées.

        Args:
            db: Session de base de données

        Returns:
            bool: True si les métriques sont activées
        """
        value = self.get_config(db, "metrics_enabled", "false")
        return value.lower() in ("true", "1", "yes", "on")

    def get_bool_config(self, db: Session, key: str, default: bool = False) -> bool:
        """Récupère une configuration booléenne.

        Args:
            db: Session de base de données
            key: Clé de la configuration
            default: Valeur par défaut

        Returns:
            bool: Valeur booléenne de la configuration
        """
        value = self.get_config(db, key, str(default).lower())
        return value.lower() in ("true", "1", "yes", "on")


# Instance globale du service
config_service = ConfigService()
