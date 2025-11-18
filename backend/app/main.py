"""Point d'entrée principal de l'application FastAPI."""
import logging
import time
from contextlib import asynccontextmanager

import aiohttp
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.database import Base, engine
from app.models import User
from app.routers import articles, auth, images, tags
from app.routers.auth import get_current_user_dependency

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Attendre que la base de données soit prête
def init_db():
    """Initialise la connexion à la base de données et crée les tables.

    Effectue plusieurs tentatives de connexion avant d'abandonner.
    Ne bloque pas le démarrage de l'application en cas d'échec.
    """
    from sqlalchemy import text

    max_retries = 30
    retry_count = 0
    while retry_count < max_retries:
        try:
            # Tester la connexion
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.info("Connexion à la base de données réussie")
                break
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                logger.error(
                    f"Impossible de se connecter à la base de données "
                    f"après {max_retries} tentatives: {e}"
                )
                # Ne pas bloquer le démarrage, on réessayera plus tard
                return
            logger.info(f"Tentative de connexion {retry_count}/{max_retries}...")
            time.sleep(2)

    # Créer les tables
    try:
        # Importer tous les modèles pour qu'ils soient enregistrés
        from app.models import Article, ArticleImage, ArticleLike, Tag, User  # noqa: F401
        Base.metadata.create_all(bind=engine)
        logger.info("Tables créées avec succès")
    except Exception as e:
        logger.error(f"Erreur lors de la création des tables: {e}")
        # Ne pas bloquer le démarrage

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gère le cycle de vie de l'application FastAPI.

    Args:
        app: Instance de l'application FastAPI

    Yields:
        None: L'application est prête à recevoir des requêtes
    """
    # Au démarrage
    logger.info("Initialisation de l'application...")
    init_db()
    yield
    # À l'arrêt
    logger.info("Arrêt de l'application...")

app = FastAPI(title="Discord Auth Blog", version="1.0.0", lifespan=lifespan)


# Middleware de sécurité pour les headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Ajoute les headers de sécurité aux réponses.

    Args:
        request: Objet Request FastAPI
        call_next: Fonction pour appeler le prochain middleware

    Returns:
        Response: Réponse avec les headers de sécurité
    """
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates
templates = Jinja2Templates(directory="templates")

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(articles.router, prefix="/api/articles", tags=["articles"])
app.include_router(images.router, prefix="/api/images", tags=["images"])
app.include_router(tags.router, prefix="/api/tags", tags=["tags"])

async def get_user_and_permissions(request: Request):
    """Helper pour obtenir l'utilisateur et ses permissions.

    Args:
        request: Objet Request FastAPI

    Returns:
        tuple: (User ou None, bool) - Utilisateur et permission de créer des articles
    """
    from app.database import get_db
    from app.services.discord import discord_service

    user = None
    can_create_articles = False
    try:
        db = next(get_db())
        user = get_current_user_dependency(request, db)
        if user:
            can_create_articles = await discord_service.check_user_has_allowed_role(
                user.discord_id
            )
    except HTTPException:
        pass
    except Exception as e:
        logger.debug(f"Erreur lors de la récupération de l'utilisateur: {e}")
    return user, can_create_articles

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Page d'accueil du blog.

    Args:
        request: Objet Request FastAPI

    Returns:
        HTMLResponse: Page d'accueil avec la liste des articles
    """
    user, can_create_articles = await get_user_and_permissions(request)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": user,
            "can_create_articles": can_create_articles,
        },
    )

@app.get("/create", response_class=HTMLResponse)
async def create_page(request: Request):
    """Page de création d'article.

    Args:
        request: Objet Request FastAPI

    Returns:
        HTMLResponse: Page de création ou page d'erreur
    """
    from app.database import get_db
    from app.services.discord import discord_service

    db = next(get_db())
    try:
        user = get_current_user_dependency(request, db)
        can_create_articles = await discord_service.check_user_has_allowed_role(
            user.discord_id
        )
        if not can_create_articles:
            return templates.TemplateResponse(
                "error.html",
                {
                    "request": request,
                    "error": (
                        "Vous n'avez pas les permissions nécessaires pour créer "
                        "des articles. Vous devez avoir un des rôles Discord autorisés."
                    ),
                },
            )
    except HTTPException:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": "Vous devez être connecté pour créer un article",
            },
        )
    return templates.TemplateResponse(
        "create.html",
        {"request": request, "user": user, "can_create_articles": True},
    )

@app.get("/manage", response_class=HTMLResponse)
async def manage_page(request: Request):
    """Page de gestion des articles.

    Args:
        request: Objet Request FastAPI

    Returns:
        HTMLResponse: Page de gestion ou page d'erreur
    """
    from app.database import get_db
    from app.services.discord import discord_service

    db = next(get_db())
    try:
        user = get_current_user_dependency(request, db)
        can_create_articles = await discord_service.check_user_has_allowed_role(
            user.discord_id
        )
        if not can_create_articles:
            return templates.TemplateResponse(
                "error.html",
                {
                    "request": request,
                    "error": (
                        "Vous n'avez pas les permissions nécessaires pour gérer "
                        "les articles. Vous devez avoir un des rôles Discord autorisés."
                    ),
                },
            )
    except HTTPException:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": "Vous devez être connecté pour gérer les articles",
            },
        )
    return templates.TemplateResponse(
        "manage.html",
        {"request": request, "user": user, "can_create_articles": True},
    )


@app.get("/edit/{article_id}", response_class=HTMLResponse)
async def edit_page(article_id: int, request: Request):
    """Page d'édition d'un article.

    Args:
        article_id: ID de l'article à modifier
        request: Objet Request FastAPI

    Returns:
        HTMLResponse: Page d'édition ou page d'erreur
    """
    from app.database import get_db
    from app.models import Article
    from app.services.discord import discord_service

    db = next(get_db())
    try:
        user = get_current_user_dependency(request, db)
        can_create_articles = await discord_service.check_user_has_allowed_role(
            user.discord_id
        )
        if not can_create_articles:
            return templates.TemplateResponse(
                "error.html",
                {
                    "request": request,
                    "error": (
                        "Vous n'avez pas les permissions nécessaires pour modifier "
                        "des articles. Vous devez avoir un des rôles Discord autorisés."
                    ),
                },
            )

        # Récupérer l'article
        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "error": "Article non trouvé"},
            )

        # Vérifier que l'utilisateur est l'auteur
        if article.author_id != user.id:
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "error": "Vous n'êtes pas l'auteur de cet article"},
            )

    except HTTPException:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": "Vous devez être connecté pour modifier un article",
            },
        )

    return templates.TemplateResponse(
        "edit.html",
        {"request": request, "user": user, "article": article, "can_create_articles": True},
    )


@app.get("/tags", response_class=HTMLResponse)
async def tags_page(request: Request):
    """Page de gestion des tags.

    Args:
        request: Objet Request FastAPI

    Returns:
        HTMLResponse: Page de gestion des tags ou page d'erreur
    """
    from app.database import get_db
    from app.services.discord import discord_service

    db = next(get_db())
    try:
        user = get_current_user_dependency(request, db)
        can_create_articles = await discord_service.check_user_has_allowed_role(
            user.discord_id
        )
        if not can_create_articles:
            return templates.TemplateResponse(
                "error.html",
                {
                    "request": request,
                    "error": (
                        "Vous n'avez pas les permissions nécessaires pour gérer "
                        "les tags. Vous devez avoir un des rôles Discord autorisés."
                    ),
                },
            )
    except HTTPException:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": "Vous devez être connecté pour gérer les tags",
            },
        )
    return templates.TemplateResponse(
        "tags.html",
        {"request": request, "user": user, "can_create_articles": True},
    )


@app.get("/article/{slug}", response_class=HTMLResponse)
async def article_page(slug: str, request: Request):
    """Page de visualisation d'un article.

    Args:
        slug: Slug de l'article
        request: Objet Request FastAPI

    Returns:
        HTMLResponse: Page de l'article ou page d'erreur
    """
    from app.database import get_db
    from app.models import Article

    db = next(get_db())
    article = db.query(Article).filter(Article.slug == slug).first()
    if not article:
        return templates.TemplateResponse(
            "error.html", {"request": request, "error": "Article non trouvé"}
        )

    # Vérifier si l'article est publié ou si l'utilisateur est l'auteur
    user, can_create_articles = await get_user_and_permissions(request)
    is_author = False
    if user:
        is_author = user.id == article.author_id

    if not article.published and not is_author:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Cet article n'est pas publié"},
        )
    return templates.TemplateResponse(
        "article.html",
        {
            "request": request,
            "article": article,
            "user": user,
            "can_create_articles": can_create_articles,
        },
    )

@app.get("/liked", response_class=HTMLResponse)
async def liked_articles_page(request: Request):
    """Page des articles aimés par l'utilisateur.

    Args:
        request: Objet Request FastAPI

    Returns:
        HTMLResponse: Page des articles aimés ou page d'erreur
    """
    from app.database import get_db

    db = next(get_db())
    try:
        user = get_current_user_dependency(request, db)
    except HTTPException:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": "Vous devez être connecté pour voir vos articles aimés",
            },
        )
    return templates.TemplateResponse(
        "liked.html",
        {"request": request, "user": user},
    )


@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """Page de profil utilisateur.

    Args:
        request: Objet Request FastAPI

    Returns:
        HTMLResponse: Page de profil ou page d'erreur
    """
    from app.database import get_db
    from app.models import Article, ArticleLike
    from app.services.discord import discord_service

    db = next(get_db())
    try:
        user = get_current_user_dependency(request, db)
        can_create_articles = await discord_service.check_user_has_allowed_role(
            user.discord_id
        )
        
        # Compter les articles créés par l'utilisateur
        articles_count = db.query(Article).filter(Article.author_id == user.id).count()
        
        # Compter les articles aimés par l'utilisateur
        liked_count = (
            db.query(ArticleLike)
            .join(Article)
            .filter(
                ArticleLike.user_id == user.id,
                Article.published == True
            )
            .count()
        )
    except HTTPException:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": "Vous devez être connecté pour voir votre profil",
            },
        )
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": user,
            "can_create_articles": can_create_articles,
            "articles_count": articles_count,
            "liked_count": liked_count,
        },
    )


@app.get("/debug", response_class=HTMLResponse)
async def debug_page(request: Request):
    """Page de debug pour voir les rôles de l'utilisateur"""
    from app.database import get_db
    from app.services.discord import discord_service
    import logging
    logger = logging.getLogger(__name__)
    
    db = next(get_db())
    
    user = None
    user_roles = []
    allowed_roles = []
    has_permission = False
    error = None
    debug_info = {}
    
    try:
        user = get_current_user_dependency(request, db)
        if user:
            logger.info(f"Debug pour l'utilisateur {user.discord_id} ({user.username})")
            
            # Vérifier si le bot peut accéder au serveur
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {"Authorization": f"Bot {settings.DISCORD_BOT_TOKEN}"}
                    url = f"https://discord.com/api/v10/guilds/{settings.DISCORD_GUILD_ID}"
                    logger.info(f"Tentative d'accès au serveur: {url}")
                    logger.info(f"Token utilisé (premiers 20 caractères): {settings.DISCORD_BOT_TOKEN[:20]}...")
                    
                    async with session.get(url, headers=headers) as response:
                        response_text = await response.text()
                        logger.info(f"Réponse serveur: status={response.status}, body={response_text[:200]}")
                        
                        if response.status == 200:
                            guild_data = await response.json()
                            debug_info["guild_name"] = guild_data.get("name", "Inconnu")
                            debug_info["guild_accessible"] = True
                        elif response.status == 401:
                            debug_info["guild_accessible"] = False
                            debug_info["guild_error"] = f"Status 401 - Token invalide ou bot non autorisé. Vérifiez que le bot token est correct et que le bot est sur le serveur."
                            try:
                                error_data = await response.json()
                                debug_info["guild_error_detail"] = error_data
                            except:
                                debug_info["guild_error_detail"] = response_text
                        elif response.status == 404:
                            debug_info["guild_accessible"] = False
                            debug_info["guild_error"] = f"Status 404 - Serveur non trouvé. Vérifiez que le Guild ID est correct et que le bot est sur ce serveur."
                        else:
                            debug_info["guild_accessible"] = False
                            debug_info["guild_error"] = f"Status {response.status}: {response_text[:200]}"
            except Exception as e:
                debug_info["guild_error"] = str(e)
                logger.error(f"Erreur lors de la vérification du serveur: {e}", exc_info=True)
            
            # Récupérer les rôles
            member = await discord_service.get_user_guild_member(user.discord_id)
            if member:
                user_roles_raw = member.get("roles", [])
                # Convertir en strings pour la comparaison
                user_roles = [str(r) for r in user_roles_raw]
                debug_info["member_found"] = True
                debug_info["member_data"] = {
                    "nick": member.get("nick"),
                    "roles": user_roles,
                    "roles_raw": user_roles_raw,
                    "roles_types": [type(r).__name__ for r in user_roles_raw],
                    "joined_at": member.get("joined_at")
                }
            else:
                debug_info["member_found"] = False
                debug_info["member_error"] = "L'utilisateur n'a pas été trouvé sur le serveur"
                user_roles = []
            
            allowed_roles = settings.ALLOWED_ROLE_IDS
            has_permission = await discord_service.check_user_has_allowed_role(user.discord_id)
            
            debug_info["guild_id"] = settings.DISCORD_GUILD_ID
            debug_info["bot_token_set"] = bool(settings.DISCORD_BOT_TOKEN)
            debug_info["client_id"] = settings.DISCORD_CLIENT_ID
    except Exception as e:
        error = str(e)
        logger.error(f"Erreur dans debug_page: {e}", exc_info=True)
    
    return templates.TemplateResponse("debug.html", {
        "request": request,
        "user": user,
        "user_roles": user_roles,
        "allowed_roles": allowed_roles,
        "has_permission": has_permission,
        "error": error,
        "debug_info": debug_info
    })

@app.get("/health")
async def health():
    """Endpoint de santé pour vérifier que l'API est opérationnelle.

    Returns:
        dict: Statut de l'API
    """
    return {"status": "ok"}

