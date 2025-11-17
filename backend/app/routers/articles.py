from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User, Article
from app.schemas import ArticleCreate, ArticleUpdate, ArticleResponse, ArticleListResponse, ArticlePreview
from app.routers.auth import get_current_user_dependency
from app.services.discord import discord_service
from datetime import datetime
import re

router = APIRouter()

def slugify(text: str) -> str:
    """Convertit un texte en slug"""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')

async def check_article_permission(user: User) -> bool:
    """Vérifie si l'utilisateur peut créer/modifier des articles"""
    return await discord_service.check_user_has_allowed_role(user.discord_id)

@router.get("/", response_model=List[ArticleListResponse])
async def list_articles(
    published_only: bool = True,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Liste des articles"""
    query = db.query(Article)
    if published_only:
        query = query.filter(Article.published == True)
    
    articles = query.order_by(Article.created_at.desc()).offset(skip).limit(limit).all()
    return articles

@router.get("/{slug}", response_model=ArticleResponse)
async def get_article(slug: str, db: Session = Depends(get_db)):
    """Récupère un article par son slug"""
    article = db.query(Article).filter(Article.slug == slug).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Ne pas vérifier published ici car on veut pouvoir voir les articles non publiés si on est l'auteur
    # La vérification sera faite côté frontend ou dans la route HTML
    
    return article

@router.post("/", response_model=ArticleResponse)
async def create_article(
    article: ArticleCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Crée un nouvel article"""
    # Vérifier les permissions
    has_permission = await check_article_permission(current_user)
    if not has_permission:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to create articles. You need one of the allowed Discord roles."
        )
    
    # Vérifier si le slug existe déjà
    existing = db.query(Article).filter(Article.slug == article.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Article with this slug already exists")
    
    # Créer l'article
    db_article = Article(
        title=article.title,
        slug=article.slug or slugify(article.title),
        content=article.content,
        excerpt=article.excerpt,
        author_id=current_user.id,
        published=article.published
    )
    db.add(db_article)
    db.commit()
    db.refresh(db_article)
    
    return db_article

@router.put("/{article_id}", response_model=ArticleResponse)
async def update_article(
    article_id: int,
    article_update: ArticleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Met à jour un article"""
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
            status_code=403,
            detail="You don't have permission to edit articles."
        )
    
    # Mettre à jour
    if article_update.title is not None:
        db_article.title = article_update.title
    if article_update.slug is not None:
        # Vérifier si le nouveau slug existe déjà
        existing = db.query(Article).filter(
            Article.slug == article_update.slug,
            Article.id != article_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Article with this slug already exists")
        db_article.slug = article_update.slug
    if article_update.content is not None:
        db_article.content = article_update.content
    if article_update.excerpt is not None:
        db_article.excerpt = article_update.excerpt
    if article_update.published is not None:
        db_article.published = article_update.published
    
    db_article.updated_at = datetime.now()
    db.commit()
    db.refresh(db_article)
    
    return db_article

@router.delete("/{article_id}")
async def delete_article(
    article_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency)
):
    """Supprime un article"""
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

@router.post("/preview", response_model=ArticlePreview)
async def preview_article(
    article: ArticlePreview,
    request: Request,
    current_user: User = Depends(get_current_user_dependency)
):
    """Prévisualise un article sans le sauvegarder"""
    # Vérifier les permissions
    has_permission = await check_article_permission(current_user)
    if not has_permission:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to preview articles. You need one of the allowed Discord roles."
        )
    
    # Générer le slug si non fourni
    if not article.slug:
        article.slug = slugify(article.title)
    
    return article

