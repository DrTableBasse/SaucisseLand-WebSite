"""Routes pour la gestion des tags."""
import logging
import re
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Tag, User
from app.routers.auth import get_current_user_dependency
from app.schemas import TagCreate, TagResponse, TagUpdate
from app.services.discord import discord_service

logger = logging.getLogger(__name__)
router = APIRouter()


def slugify(text: str) -> str:
    """Convertit un texte en slug URL-friendly.

    Args:
        text: Texte à convertir

    Returns:
        str: Slug généré
    """
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")


async def check_tag_permission(user: User) -> bool:
    """Vérifie si l'utilisateur peut gérer les tags.

    Args:
        user: Utilisateur à vérifier

    Returns:
        bool: True si l'utilisateur a les permissions
    """
    return await discord_service.check_user_has_allowed_role(user.discord_id)


@router.get("/", response_model=List[TagResponse])
async def list_tags(
    db: Session = Depends(get_db),
):
    """Liste tous les tags.

    Args:
        db: Session de base de données

    Returns:
        List[TagResponse]: Liste des tags
    """
    tags = db.query(Tag).order_by(Tag.name).all()
    return tags


@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(
    tag_id: int,
    db: Session = Depends(get_db),
):
    """Récupère un tag par son ID.

    Args:
        tag_id: ID du tag
        db: Session de base de données

    Returns:
        TagResponse: Tag trouvé

    Raises:
        HTTPException: Si le tag n'existe pas
    """
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.post("/", response_model=TagResponse)
async def create_tag(
    tag: TagCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Crée un nouveau tag.

    Args:
        tag: Données du tag à créer
        request: Objet Request FastAPI
        db: Session de base de données
        current_user: Utilisateur actuel

    Returns:
        TagResponse: Tag créé

    Raises:
        HTTPException: Si l'utilisateur n'a pas les permissions ou si le tag existe déjà
    """
    # Vérifier les permissions
    try:
        has_permission = await check_tag_permission(current_user)
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Vous n'avez pas les permissions nécessaires pour créer des tags. "
                    "Vous devez avoir un des rôles Discord autorisés. "
                    "Vérifiez que votre rôle est dans ALLOWED_ROLE_IDS du fichier .env"
                ),
            )
    except Exception as e:
        logger.error(f"Erreur lors de la vérification des permissions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la vérification des permissions: {str(e)}"
        )

    # Générer le slug si non fourni
    slug = tag.slug or slugify(tag.name)

    # Vérifier si le tag existe déjà (par nom ou slug)
    existing = db.query(Tag).filter(
        (Tag.name == tag.name) | (Tag.slug == slug)
    ).first()
    if existing:
        raise HTTPException(
            status_code=400, detail="Tag with this name or slug already exists"
        )

    # Créer le tag
    db_tag = Tag(
        name=tag.name,
        slug=slug,
        description=tag.description,
        color=tag.color or "#3b82f6",
    )
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)

    return db_tag


@router.put("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: int,
    tag_update: TagUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Met à jour un tag.

    Args:
        tag_id: ID du tag à mettre à jour
        tag_update: Données de mise à jour
        request: Objet Request FastAPI
        db: Session de base de données
        current_user: Utilisateur actuel

    Returns:
        TagResponse: Tag mis à jour

    Raises:
        HTTPException: Si le tag n'existe pas, l'utilisateur n'est pas autorisé
            ou le nom/slug existe déjà
    """
    # Vérifier les permissions
    has_permission = await check_tag_permission(current_user)
    if not has_permission:
        raise HTTPException(
            status_code=403, detail="You don't have permission to edit tags."
        )

    db_tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not db_tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    # Mettre à jour
    if tag_update.name is not None:
        # Vérifier si le nouveau nom existe déjà
        existing = (
            db.query(Tag)
            .filter(Tag.name == tag_update.name, Tag.id != tag_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=400, detail="Tag with this name already exists"
            )
        db_tag.name = tag_update.name

    if tag_update.slug is not None:
        # Vérifier si le nouveau slug existe déjà
        existing = (
            db.query(Tag)
            .filter(Tag.slug == tag_update.slug, Tag.id != tag_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=400, detail="Tag with this slug already exists"
            )
        db_tag.slug = tag_update.slug
    elif tag_update.name is not None:
        # Générer le slug si le nom a changé mais pas le slug
        db_tag.slug = slugify(tag_update.name)

    if tag_update.description is not None:
        db_tag.description = tag_update.description
    if tag_update.color is not None:
        db_tag.color = tag_update.color

    db.commit()
    db.refresh(db_tag)

    return db_tag


@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Supprime un tag.

    Args:
        tag_id: ID du tag à supprimer
        request: Objet Request FastAPI
        db: Session de base de données
        current_user: Utilisateur actuel

    Returns:
        dict: Message de confirmation

    Raises:
        HTTPException: Si le tag n'existe pas ou l'utilisateur n'est pas autorisé
    """
    # Vérifier les permissions
    has_permission = await check_tag_permission(current_user)
    if not has_permission:
        raise HTTPException(
            status_code=403, detail="You don't have permission to delete tags."
        )

    db_tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not db_tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    db.delete(db_tag)
    db.commit()

    return {"message": "Tag deleted"}

