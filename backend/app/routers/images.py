"""Routes pour la gestion des images d'articles."""
import os
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from PIL import Image
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Article, ArticleImage, User
from app.routers.auth import get_current_user_dependency
from app.schemas import ImageResponse
from app.services.discord import discord_service

router = APIRouter()

# Créer le dossier uploads s'il n'existe pas
UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


async def check_article_permission(user: User) -> bool:
    """Vérifie si l'utilisateur peut créer/modifier des articles.

    Args:
        user: Utilisateur à vérifier

    Returns:
        bool: True si l'utilisateur a les permissions
    """
    return await discord_service.check_user_has_allowed_role(user.discord_id)

@router.post("/upload", response_model=ImageResponse)
async def upload_image(
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Upload une image.

    Args:
        file: Fichier image à uploader
        request: Objet Request FastAPI
        db: Session de base de données
        current_user: Utilisateur actuel

    Returns:
        ImageResponse: Informations de l'image uploadée

    Raises:
        HTTPException: Si l'utilisateur n'a pas les permissions, le fichier est invalide
            ou trop volumineux
    """
    # Vérifier les permissions
    has_permission = await check_article_permission(current_user)
    if not has_permission:
        raise HTTPException(
            status_code=403, detail="You don't have permission to upload images."
        )

    # Vérifier le type de fichier
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"File type not allowed. "
                f"Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            ),
        )

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"MIME type not allowed. "
                f"Allowed types: {', '.join(ALLOWED_MIME_TYPES)}"
            ),
        )

    # Lire le fichier
    contents = await file.read()
    file_size = len(contents)

    if file_size > settings.MAX_UPLOAD_SIZE:
        max_size_mb = settings.MAX_UPLOAD_SIZE / 1024 / 1024
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {max_size_mb}MB",
        )

    # Générer un nom de fichier unique
    filename = f"{uuid.uuid4()}{file_ext}"
    file_path = UPLOAD_DIR / filename

    # Sauvegarder le fichier
    with open(file_path, "wb") as f:
        f.write(contents)

    # Optionnel: redimensionner l'image si nécessaire
    try:
        img = Image.open(file_path)
        # Vous pouvez ajouter du redimensionnement ici si nécessaire
        img.close()
    except Exception as e:
        # Si l'image est corrompue, supprimer le fichier
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(
            status_code=400, detail=f"Invalid image file: {str(e)}"
        )

    # Créer l'entrée en base de données
    db_image = ArticleImage(
        filename=filename,
        original_filename=file.filename,
        file_path=str(file_path),
        mime_type=file.content_type,
        file_size=file_size,
    )
    db.add(db_image)
    db.commit()
    db.refresh(db_image)

    return db_image

@router.get("/{image_id}", response_model=ImageResponse)
async def get_image(image_id: int, db: Session = Depends(get_db)):
    """Récupère les informations d'une image.

    Args:
        image_id: ID de l'image
        db: Session de base de données

    Returns:
        ImageResponse: Informations de l'image

    Raises:
        HTTPException: Si l'image n'existe pas
    """
    image = db.query(ArticleImage).filter(ArticleImage.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    return image


@router.get("/article/{article_id}", response_model=List[ImageResponse])
async def get_article_images(article_id: int, db: Session = Depends(get_db)):
    """Récupère toutes les images d'un article.

    Args:
        article_id: ID de l'article
        db: Session de base de données

    Returns:
        List[ImageResponse]: Liste des images de l'article
    """
    images = (
        db.query(ArticleImage)
        .filter(ArticleImage.article_id == article_id)
        .all()
    )
    return images


@router.delete("/{image_id}")
async def delete_image(
    image_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Supprime une image.

    Args:
        image_id: ID de l'image à supprimer
        request: Objet Request FastAPI
        db: Session de base de données
        current_user: Utilisateur actuel

    Returns:
        dict: Message de confirmation

    Raises:
        HTTPException: Si l'utilisateur n'a pas les permissions ou l'image n'existe pas
    """
    # Vérifier les permissions
    has_permission = await check_article_permission(current_user)
    if not has_permission:
        raise HTTPException(
            status_code=403, detail="You don't have permission to delete images."
        )

    image = db.query(ArticleImage).filter(ArticleImage.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Supprimer le fichier
    if os.path.exists(image.file_path):
        os.remove(image.file_path)

    # Supprimer de la base de données
    db.delete(image)
    db.commit()

    return {"message": "Image deleted"}

