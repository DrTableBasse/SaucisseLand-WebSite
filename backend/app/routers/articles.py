"""Routes pour la gestion des articles."""
import re
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Article, ArticleLike, Tag, User
from app.routers.auth import get_current_user_dependency
from app.schemas import (
    ArticleCreate,
    ArticleListResponse,
    ArticleResponse,
    ArticleUpdate,
)
from app.services.discord import discord_service

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


async def check_article_permission(user: User) -> bool:
    """Vérifie si l'utilisateur peut créer/modifier des articles.

    Args:
        user: Utilisateur à vérifier

    Returns:
        bool: True si l'utilisateur a les permissions
    """
    return await discord_service.check_user_has_allowed_role(user.discord_id)

@router.get("/", response_model=List[ArticleListResponse])
async def list_articles(
    published_only: bool = True,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Liste des articles.

    Args:
        published_only: Afficher uniquement les articles publiés
        skip: Nombre d'articles à sauter (pagination)
        limit: Nombre maximum d'articles à retourner
        db: Session de base de données

    Returns:
        List[ArticleListResponse]: Liste des articles
    """
    query = db.query(Article)
    if published_only:
        query = query.filter(Article.published == True)

    articles = (
        query.order_by(Article.created_at.desc()).offset(skip).limit(limit).all()
    )
    return articles


@router.get("/liked", response_model=List[ArticleListResponse])
async def get_liked_articles(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Récupère tous les articles likés par l'utilisateur actuel.

    Args:
        request: Objet Request FastAPI
        db: Session de base de données
        current_user: Utilisateur actuel

    Returns:
        List[ArticleListResponse]: Liste des articles likés

    Raises:
        HTTPException: Si l'utilisateur n'est pas connecté
    """
    # Récupérer les articles likés par l'utilisateur, triés par date de like (plus récents en premier)
    liked_articles = (
        db.query(Article)
        .join(ArticleLike, Article.id == ArticleLike.article_id)
        .filter(
            ArticleLike.user_id == current_user.id,
            Article.published == True  # Seulement les articles publiés
        )
        .order_by(ArticleLike.created_at.desc())
        .all()
    )
    return liked_articles


@router.get("/{slug}", response_model=ArticleResponse)
async def get_article(slug: str, db: Session = Depends(get_db)):
    """Récupère un article par son slug.

    Args:
        slug: Slug de l'article
        db: Session de base de données

    Returns:
        ArticleResponse: Article trouvé

    Raises:
        HTTPException: Si l'article n'existe pas
    """
    article = db.query(Article).filter(Article.slug == slug).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Ne pas vérifier published ici car on veut pouvoir voir les articles
    # non publiés si on est l'auteur. La vérification sera faite côté
    # frontend ou dans la route HTML

    return article

@router.post("/", response_model=ArticleResponse)
async def create_article(
    article: ArticleCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Crée un nouvel article.

    Args:
        article: Données de l'article à créer
        request: Objet Request FastAPI
        db: Session de base de données
        current_user: Utilisateur actuel

    Returns:
        ArticleResponse: Article créé

    Raises:
        HTTPException: Si l'utilisateur n'a pas les permissions ou si le slug existe
    """
    # Vérifier les permissions
    has_permission = await check_article_permission(current_user)
    if not has_permission:
        raise HTTPException(
            status_code=403,
            detail=(
                "You don't have permission to create articles. "
                "You need one of the allowed Discord roles."
            ),
        )

    # Générer le slug si non fourni
    slug = article.slug or slugify(article.title)

    # Vérifier si le slug existe déjà
    existing = db.query(Article).filter(Article.slug == slug).first()
    if existing:
        raise HTTPException(
            status_code=400, detail="Article with this slug already exists"
        )

    # Créer l'article
    db_article = Article(
        title=article.title,
        slug=slug,
        content=article.content,
        excerpt=article.excerpt,
        author_id=current_user.id,
        published=article.published,
    )
    db.add(db_article)
    db.commit()
    db.refresh(db_article)

    # Associer les tags si fournis
    if article.tag_ids:
        tags = db.query(Tag).filter(Tag.id.in_(article.tag_ids)).all()
        db_article.tags = tags
        db.commit()
        db.refresh(db_article)

    return db_article

@router.put("/{article_id}", response_model=ArticleResponse)
async def update_article(
    article_id: int,
    article_update: ArticleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Met à jour un article.

    Args:
        article_id: ID de l'article à mettre à jour
        article_update: Données de mise à jour
        request: Objet Request FastAPI
        db: Session de base de données
        current_user: Utilisateur actuel

    Returns:
        ArticleResponse: Article mis à jour

    Raises:
        HTTPException: Si l'article n'existe pas, l'utilisateur n'est pas autorisé
            ou le slug existe déjà
    """
    db_article = db.query(Article).filter(Article.id == article_id).first()
    if not db_article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Vérifier que l'utilisateur est l'auteur ou a les permissions
    if db_article.author_id != current_user.id:
        has_permission = await check_article_permission(current_user)
        if not has_permission:
            raise HTTPException(status_code=403, detail="Not authorized")

    # Vérifier les permissions pour modifier
    has_permission = await check_article_permission(current_user)
    if not has_permission:
        raise HTTPException(
            status_code=403, detail="You don't have permission to edit articles."
        )

    # Mettre à jour
    if article_update.title is not None:
        db_article.title = article_update.title
    if article_update.slug is not None:
        # Vérifier si le nouveau slug existe déjà
        existing = (
            db.query(Article)
            .filter(Article.slug == article_update.slug, Article.id != article_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=400, detail="Article with this slug already exists"
            )
        db_article.slug = article_update.slug
    if article_update.content is not None:
        db_article.content = article_update.content
    if article_update.excerpt is not None:
        db_article.excerpt = article_update.excerpt
    if article_update.published is not None:
        db_article.published = article_update.published

    # Mettre à jour les tags si fournis
    if article_update.tag_ids is not None:
        tags = db.query(Tag).filter(Tag.id.in_(article_update.tag_ids)).all()
        db_article.tags = tags

    db_article.updated_at = datetime.now()
    db.commit()
    db.refresh(db_article)

    return db_article

@router.delete("/{article_id}")
async def delete_article(
    article_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Supprime un article.

    Args:
        article_id: ID de l'article à supprimer
        request: Objet Request FastAPI
        db: Session de base de données
        current_user: Utilisateur actuel

    Returns:
        dict: Message de confirmation

    Raises:
        HTTPException: Si l'article n'existe pas ou l'utilisateur n'est pas autorisé
    """
    db_article = db.query(Article).filter(Article.id == article_id).first()
    if not db_article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Vérifier que l'utilisateur est l'auteur ou a les permissions
    if db_article.author_id != current_user.id:
        has_permission = await check_article_permission(current_user)
        if not has_permission:
            raise HTTPException(status_code=403, detail="Not authorized")

    db.delete(db_article)
    db.commit()

    return {"message": "Article deleted"}


@router.post("/{article_id}/toggle-published", response_model=ArticleResponse)
async def toggle_published(
    article_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Bascule l'état de publication d'un article.

    Args:
        article_id: ID de l'article
        request: Objet Request FastAPI
        db: Session de base de données
        current_user: Utilisateur actuel

    Returns:
        ArticleResponse: Article mis à jour

    Raises:
        HTTPException: Si l'article n'existe pas ou l'utilisateur n'est pas autorisé
    """
    db_article = db.query(Article).filter(Article.id == article_id).first()
    if not db_article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Vérifier que l'utilisateur est l'auteur ou a les permissions
    if db_article.author_id != current_user.id:
        has_permission = await check_article_permission(current_user)
        if not has_permission:
            raise HTTPException(status_code=403, detail="Not authorized")

    # Vérifier les permissions pour modifier
    has_permission = await check_article_permission(current_user)
    if not has_permission:
        raise HTTPException(
            status_code=403, detail="You don't have permission to edit articles."
        )

    # Bascule l'état
    db_article.published = not db_article.published
    db_article.updated_at = datetime.now()
    db.commit()
    db.refresh(db_article)

    return db_article


@router.post("/{article_id}/increment-views")
async def increment_views(
    article_id: int,
    db: Session = Depends(get_db),
):
    """Incrémente le compteur de vues d'un article.

    Args:
        article_id: ID de l'article
        db: Session de base de données

    Returns:
        dict: Nombre de vues mis à jour

    Raises:
        HTTPException: Si l'article n'existe pas
    """
    db_article = db.query(Article).filter(Article.id == article_id).first()
    if not db_article:
        raise HTTPException(status_code=404, detail="Article not found")

    db_article.views += 1
    db.commit()
    db.refresh(db_article)

    return {"views": db_article.views}


@router.post("/{article_id}/like")
async def toggle_like(
    article_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Ajoute ou retire un like à un article.

    Args:
        article_id: ID de l'article
        request: Objet Request FastAPI
        db: Session de base de données
        current_user: Utilisateur actuel

    Returns:
        dict: Nombre de likes mis à jour et état du like

    Raises:
        HTTPException: Si l'article n'existe pas
    """
    db_article = db.query(Article).filter(Article.id == article_id).first()
    if not db_article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Vérifier si l'utilisateur a déjà liké cet article
    existing_like = (
        db.query(ArticleLike)
        .filter(
            ArticleLike.article_id == article_id,
            ArticleLike.user_id == current_user.id
        )
        .first()
    )

    if existing_like:
        # Retirer le like
        db.delete(existing_like)
        db_article.likes = max(0, db_article.likes - 1)
        liked = False
    else:
        # Ajouter le like
        new_like = ArticleLike(
            article_id=article_id,
            user_id=current_user.id
        )
        db.add(new_like)
        db_article.likes += 1
        liked = True

    db.commit()
    db.refresh(db_article)

    return {"likes": db_article.likes, "liked": liked}


@router.get("/{article_id}/like-status")
async def get_like_status(
    article_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Récupère le statut du like pour l'utilisateur actuel.

    Args:
        article_id: ID de l'article
        request: Objet Request FastAPI
        db: Session de base de données

    Returns:
        dict: Statut du like (liked: bool) et nombre total de likes
    """
    from app.routers.auth import get_current_user_dependency

    db_article = db.query(Article).filter(Article.id == article_id).first()
    if not db_article:
        raise HTTPException(status_code=404, detail="Article not found")

    liked = False
    try:
        current_user = get_current_user_dependency(request, db)
        existing_like = (
            db.query(ArticleLike)
            .filter(
                ArticleLike.article_id == article_id,
                ArticleLike.user_id == current_user.id
            )
            .first()
        )
        liked = existing_like is not None
    except HTTPException:
        # Utilisateur non connecté
        pass

    return {"liked": liked, "likes": db_article.likes}


@router.get("/manage/all", response_model=List[ArticleListResponse])
async def get_all_articles_for_management(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Récupère tous les articles pour la gestion (y compris non publiés).

    Args:
        request: Objet Request FastAPI
        db: Session de base de données
        current_user: Utilisateur actuel

    Returns:
        List[ArticleListResponse]: Liste de tous les articles

    Raises:
        HTTPException: Si l'utilisateur n'a pas les permissions
    """
    # Vérifier les permissions
    has_permission = await check_article_permission(current_user)
    if not has_permission:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to manage articles.",
        )

    # Récupérer tous les articles, triés par date de création (plus récents en premier)
    articles = (
        db.query(Article)
        .order_by(Article.created_at.desc())
        .all()
    )
    return articles

