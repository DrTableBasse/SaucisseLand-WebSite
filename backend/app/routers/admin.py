"""Router pour l'administration des configurations."""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AppConfig, User
from app.routers.auth import get_current_user_dependency
from app.schemas import AppConfigCreate, AppConfigResponse, AppConfigUpdate, MetricsToggleRequest
from app.services.config_service import config_service
from app.services.discord import discord_service

logger = logging.getLogger(__name__)

router = APIRouter()


async def check_admin_permission(user: User) -> bool:
    """Vérifie si l'utilisateur a les permissions d'administration.

    Args:
        user: Utilisateur à vérifier

    Returns:
        bool: True si l'utilisateur a les permissions
    """
    return await discord_service.check_user_has_allowed_role(user.discord_id)


@router.get("/configs", response_model=List[AppConfigResponse])
async def list_configs(
    request: Request,
    category: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Liste toutes les configurations.

    Args:
        request: Objet Request FastAPI
        category: Filtrer par catégorie (optionnel)
        db: Session de base de données
        current_user: Utilisateur actuel

    Returns:
        List[AppConfigResponse]: Liste des configurations

    Raises:
        HTTPException: Si l'utilisateur n'a pas les permissions
    """
    if not await check_admin_permission(current_user):
        raise HTTPException(status_code=403, detail="Permission denied")

    query = db.query(AppConfig)
    if category:
        query = query.filter(AppConfig.category == category)
    
    configs = query.all()
    return configs


@router.get("/configs/{key}", response_model=AppConfigResponse)
async def get_config(
    key: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Récupère une configuration spécifique.

    Args:
        key: Clé de la configuration
        request: Objet Request FastAPI
        db: Session de base de données
        current_user: Utilisateur actuel

    Returns:
        AppConfigResponse: Configuration

    Raises:
        HTTPException: Si l'utilisateur n'a pas les permissions ou si la config n'existe pas
    """
    if not await check_admin_permission(current_user):
        raise HTTPException(status_code=403, detail="Permission denied")

    config = db.query(AppConfig).filter(AppConfig.key == key).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    return config


@router.post("/configs", response_model=AppConfigResponse)
async def create_config(
    config: AppConfigCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Crée une nouvelle configuration.

    Args:
        config: Données de la configuration
        request: Objet Request FastAPI
        db: Session de base de données
        current_user: Utilisateur actuel

    Returns:
        AppConfigResponse: Configuration créée

    Raises:
        HTTPException: Si l'utilisateur n'a pas les permissions ou si la clé existe déjà
    """
    if not await check_admin_permission(current_user):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Vérifier si la clé existe déjà
    existing = db.query(AppConfig).filter(AppConfig.key == config.key).first()
    if existing:
        raise HTTPException(status_code=400, detail="Configuration key already exists")

    new_config = config_service.set_config(
        db=db,
        key=config.key,
        value=config.value,
        description=config.description,
        category=config.category,
        is_sensitive=config.is_sensitive,
        updated_by=current_user.id,
    )

    return new_config


@router.put("/configs/{key}", response_model=AppConfigResponse)
async def update_config(
    key: str,
    config_update: AppConfigUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Met à jour une configuration existante.

    Args:
        key: Clé de la configuration
        config_update: Données de mise à jour
        request: Objet Request FastAPI
        db: Session de base de données
        current_user: Utilisateur actuel

    Returns:
        AppConfigResponse: Configuration mise à jour

    Raises:
        HTTPException: Si l'utilisateur n'a pas les permissions ou si la config n'existe pas
    """
    if not await check_admin_permission(current_user):
        raise HTTPException(status_code=403, detail="Permission denied")

    existing = db.query(AppConfig).filter(AppConfig.key == key).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Configuration not found")

    # Mettre à jour uniquement les champs fournis
    update_data = config_update.model_dump(exclude_unset=True)
    
    if "value" in update_data:
        existing.value = update_data["value"]
    if "description" in update_data:
        existing.description = update_data["description"]
    if "category" in update_data:
        existing.category = update_data["category"]
    if "is_sensitive" in update_data:
        existing.is_sensitive = update_data["is_sensitive"]
    
    existing.updated_by = current_user.id

    db.commit()
    db.refresh(existing)

    # Mettre à jour le cache
    config_service._cache[key] = existing.value

    logger.info(f"Configuration '{key}' mise à jour par {current_user.username}")
    return existing


@router.delete("/configs/{key}")
async def delete_config(
    key: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Supprime une configuration.

    Args:
        key: Clé de la configuration
        request: Objet Request FastAPI
        db: Session de base de données
        current_user: Utilisateur actuel

    Returns:
        dict: Message de confirmation

    Raises:
        HTTPException: Si l'utilisateur n'a pas les permissions ou si la config n'existe pas
    """
    if not await check_admin_permission(current_user):
        raise HTTPException(status_code=403, detail="Permission denied")

    success = config_service.delete_config(db, key)
    if not success:
        raise HTTPException(status_code=404, detail="Configuration not found")

    logger.info(f"Configuration '{key}' supprimée par {current_user.username}")
    return {"message": f"Configuration '{key}' deleted successfully"}


@router.post("/configs/reload-cache")
async def reload_cache(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Recharge le cache des configurations.

    Args:
        request: Objet Request FastAPI
        db: Session de base de données
        current_user: Utilisateur actuel

    Returns:
        dict: Message de confirmation

    Raises:
        HTTPException: Si l'utilisateur n'a pas les permissions
    """
    if not await check_admin_permission(current_user):
        raise HTTPException(status_code=403, detail="Permission denied")

    config_service.reload_cache(db)
    return {"message": "Cache reloaded successfully"}


@router.get("/metrics/status")
async def get_metrics_status(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Récupère le statut d'activation des métriques.

    Args:
        request: Objet Request FastAPI
        db: Session de base de données
        current_user: Utilisateur actuel

    Returns:
        dict: Statut des métriques

    Raises:
        HTTPException: Si l'utilisateur n'a pas les permissions
    """
    if not await check_admin_permission(current_user):
        raise HTTPException(status_code=403, detail="Permission denied")

    enabled = config_service.is_metrics_enabled(db)
    return {"metrics_enabled": enabled}


@router.post("/metrics/toggle")
async def toggle_metrics(
    request: Request,
    toggle_data: MetricsToggleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Active ou désactive les métriques.

    Args:
        request: Objet Request FastAPI
        toggle_data: Données de la requête contenant enabled
        db: Session de base de données
        current_user: Utilisateur actuel

    Returns:
        dict: Nouveau statut des métriques

    Raises:
        HTTPException: Si l'utilisateur n'a pas les permissions
    """
    if not await check_admin_permission(current_user):
        raise HTTPException(status_code=403, detail="Permission denied")

    enabled = toggle_data.enabled

    config_service.set_config(
        db=db,
        key="metrics_enabled",
        value=str(enabled).lower(),
        description="Active ou désactive l'exportation des métriques pour Grafana",
        category="metrics",
        is_sensitive=False,
        updated_by=current_user.id,
    )

    logger.info(f"Métriques {'activées' if enabled else 'désactivées'} par {current_user.username}")
    return {"metrics_enabled": enabled}
