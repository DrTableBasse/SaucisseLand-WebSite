"""Point d'entrée principal de l'application FastAPI."""
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime

import aiohttp
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
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
        from app.models import AppConfig, Article, ArticleImage, ArticleLike, Tag, User  # noqa: F401
        Base.metadata.create_all(bind=engine)
        logger.info("Tables créées avec succès")
        
        # Initialiser le cache des configurations
        from app.services.config_service import config_service
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            config_service.reload_cache(db)
        finally:
            db.close()
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

# Favicon
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Route pour servir le favicon."""
    import os
    favicon_path = os.path.join("static", "favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/x-icon")
    raise HTTPException(status_code=404, detail="Favicon not found")

# Routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(articles.router, prefix="/api/articles", tags=["articles"])
app.include_router(images.router, prefix="/api/images", tags=["images"])
app.include_router(tags.router, prefix="/api/tags", tags=["tags"])

# Import admin router
from app.routers import admin
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])

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

    # Convertir les tags en dictionnaires pour la sérialisation JSON
    article_tags_dict = [
        {"id": tag.id, "name": tag.name, "slug": tag.slug, "color": tag.color, "description": tag.description}
        for tag in article.tags
    ]
    
    return templates.TemplateResponse(
        "edit.html",
        {
            "request": request,
            "user": user,
            "article": article,
            "article_tags_json": article_tags_dict,
            "can_create_articles": True
        },
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
    # Vérifier que discord_id existe et n'est pas vide
    logger.info(f"Profil de l'utilisateur {user.username}: discord_id={user.discord_id}, type={type(user.discord_id)}")
    if not user.discord_id:
        logger.warning(f"ATTENTION: discord_id est vide pour l'utilisateur {user.username} (ID: {user.id})")
    
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

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """Page d'administration des configurations.

    Args:
        request: Objet Request FastAPI

    Returns:
        HTMLResponse: Page d'administration ou page d'erreur
    """
    from app.database import get_db
    from app.services.discord import discord_service

    db = next(get_db())
    user = None
    can_create_articles = False
    
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
                        "Vous n'avez pas les permissions nécessaires pour accéder à l'administration. "
                        "Vous devez avoir un des rôles Discord autorisés."
                    ),
                },
            )
    except HTTPException:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": "Vous devez être connecté pour accéder à l'administration",
            },
        )
    
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "user": user,
            "can_create_articles": can_create_articles,
        },
    )


@app.get("/moderation", response_class=HTMLResponse)
async def moderation_page(request: Request):
    """Page de modération Discord.

    Args:
        request: Objet Request FastAPI

    Returns:
        HTMLResponse: Page de modération ou page d'erreur
    """
    from app.database import get_db
    from app.services.discord import discord_service

    db = next(get_db())
    user = None
    can_create_articles = False
    
    try:
        user = get_current_user_dependency(request, db)
        can_create_articles = await discord_service.check_user_has_allowed_role(
            user.discord_id
        )
    except HTTPException:
        pass
    
    return templates.TemplateResponse(
        "moderation.html",
        {
            "request": request,
            "user": user,
            "can_create_articles": can_create_articles,
        },
    )

@app.get("/api/moderation/search-users", response_class=JSONResponse)
async def search_users_api(request: Request, q: str = ""):
    """API pour rechercher des utilisateurs Discord avec autocomplétion.
    
    Args:
        request: Objet Request FastAPI
        q: Terme de recherche (pseudo Discord)
    
    Returns:
        JSON: Liste des utilisateurs trouvés avec leurs informations
    """
    from app.database import get_db
    from app.services.discord import discord_service
    
    db = next(get_db())
    
    try:
        # Vérifier l'authentification
        user = get_current_user_dependency(request, db)
        
        # Rechercher les utilisateurs
        users = await discord_service.search_users_by_username(q, limit=10)
        
        return {"users": users}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur dans /api/moderation/search-users: {e}")
        return {"users": []}

@app.delete("/api/moderation/delete-warn/{warn_id}")
async def delete_warn_api(request: Request, warn_id: int):
    """API pour supprimer un avertissement via le bot Hermes.

    Args:
        request: Objet Request FastAPI
        warn_id: ID de l'avertissement à supprimer

    Returns:
        JSON: Résultat de l'opération
    """
    logger.info(f"DELETE /api/moderation/delete-warn/{warn_id} appelé")
    from app.database import get_db
    import os
    import aiohttp
    
    db = next(get_db())
    
    try:
        # Vérifier l'authentification
        logger.info(f"Vérification de l'authentification pour la suppression du warn {warn_id}")
        user = get_current_user_dependency(request, db)
        logger.info(f"Utilisateur authentifié: {user.username} (ID: {user.discord_id})")
        
        # Configuration de l'API Hermes
        hermes_api_url = os.getenv("HERMES_API_URL", "http://localhost:8001")
        hermes_api_token = os.getenv("HERMES_API_TOKEN")
        
        logger.info(f"Configuration API: URL={hermes_api_url}, Token présent={bool(hermes_api_token)}")
        
        if not hermes_api_token:
            logger.error("HERMES_API_TOKEN manquant")
            raise HTTPException(
                status_code=500,
                detail="Configuration serveur manquante (HERMES_API_TOKEN)"
            )
        
        # Appeler l'API Hermes
        logger.info(f"Appel de l'API Hermes pour supprimer le warn {warn_id}")
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"{hermes_api_url}/warns/{warn_id}",
                headers={
                    "Authorization": f"Bearer {hermes_api_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "moderator_id": int(user.discord_id),
                    "moderator_name": user.username,
                },
            ) as response:
                logger.info(f"Réponse de l'API Hermes: status={response.status}")
                data = await response.json()
                logger.info(f"Données reçues de l'API Hermes: {data}")
                
                if not response.ok:
                    error_message = data.get("detail", "Erreur lors de l'appel à l'API Hermes")
                    logger.error(f"Erreur de l'API Hermes: {error_message}")
                    raise HTTPException(status_code=response.status, detail=error_message)
                
                logger.info(f"Warn {warn_id} supprimé avec succès, retour des données")
                return data
                
    except HTTPException as e:
        logger.error(f"HTTPException levée: {e.status_code} - {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Erreur dans /api/moderation/delete-warn/{warn_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.put("/api/moderation/update-warn/{warn_id}", response_class=JSONResponse)
async def update_warn_reason_api(request: Request, warn_id: int):
    """API pour mettre à jour la raison d'un avertissement via le bot Hermes.

    Args:
        request: Objet Request FastAPI
        warn_id: ID de l'avertissement à modifier

    Returns:
        JSON: Résultat de l'opération
    """
    logger.info(f"PUT /api/moderation/update-warn/{warn_id} appelé")
    from app.database import get_db
    import os
    import aiohttp
    
    db = next(get_db())
    
    try:
        user = get_current_user_dependency(request, db)
        logger.info(f"Utilisateur authentifié: {user.username} (ID: {user.discord_id})")
        
        # Récupérer les données de la requête
        try:
            body = await request.json()
            logger.info(f"Body reçu: {body}")
        except Exception as e:
            logger.error(f"Erreur lors de la lecture du body: {e}")
            raise HTTPException(status_code=400, detail="Body JSON invalide ou manquant")
        
        new_reason = body.get("reason", "")
        
        if not new_reason:
            logger.warning("Raison manquante dans la requête")
            raise HTTPException(status_code=400, detail="La raison est requise")
        
        logger.info(f"Raison à mettre à jour: {new_reason}")
        
        # Configuration de l'API Hermes
        hermes_api_url = os.getenv("HERMES_API_URL", "http://localhost:8001")
        hermes_api_token = os.getenv("HERMES_API_TOKEN")
        
        if not hermes_api_token:
            raise HTTPException(
                status_code=500,
                detail="Configuration serveur manquante (HERMES_API_TOKEN)"
            )
        
        # Appeler l'API Hermes
        logger.info(f"Appel de l'API Hermes: PUT {hermes_api_url}/warns/{warn_id}")
        async with aiohttp.ClientSession() as session:
            async with session.put(
                f"{hermes_api_url}/warns/{warn_id}",
                headers={
                    "Authorization": f"Bearer {hermes_api_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "reason": new_reason,
                    "moderator_id": int(user.discord_id),
                    "moderator_name": user.username,
                },
            ) as response:
                logger.info(f"Réponse de l'API Hermes: status={response.status}")
                data = await response.json()
                logger.info(f"Données reçues de l'API Hermes: {data}")
                
                if not response.ok:
                    error_message = data.get("detail", "Erreur lors de l'appel à l'API Hermes")
                    logger.error(f"Erreur de l'API Hermes: {error_message}")
                    raise HTTPException(status_code=response.status, detail=error_message)
                
                logger.info(f"Warn {warn_id} mis à jour avec succès")
                return data
                
    except HTTPException as e:
        logger.error(f"HTTPException dans /api/moderation/update-warn/{warn_id}: {e.status_code} - {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Erreur dans /api/moderation/update-warn/{warn_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.delete("/api/moderation/bulk-delete-warns")
async def bulk_delete_warns_api(request: Request):
    """API pour supprimer plusieurs avertissements en une fois via le bot Hermes.

    Args:
        request: Objet Request FastAPI

    Returns:
        JSON: Résultat de l'opération
    """
    logger.info(f"DELETE /api/moderation/bulk-delete-warns appelé")
    from app.database import get_db
    import os
    import aiohttp
    
    db = next(get_db())
    
    try:
        user = get_current_user_dependency(request, db)
        logger.info(f"Utilisateur authentifié: {user.username} (ID: {user.discord_id})")
        
        # Récupérer les données de la requête
        body = await request.json()
        warn_ids = body.get("warn_ids", [])
        
        if not warn_ids or not isinstance(warn_ids, list):
            raise HTTPException(status_code=400, detail="warn_ids doit être une liste non vide")
        
        # Configuration de l'API Hermes
        hermes_api_url = os.getenv("HERMES_API_URL", "http://localhost:8001")
        hermes_api_token = os.getenv("HERMES_API_TOKEN")
        
        if not hermes_api_token:
            raise HTTPException(
                status_code=500,
                detail="Configuration serveur manquante (HERMES_API_TOKEN)"
            )
        
        # Appeler l'API Hermes (utiliser POST car DELETE ne supporte pas le body)
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{hermes_api_url}/warns/bulk",
                headers={
                    "Authorization": f"Bearer {hermes_api_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "warn_ids": warn_ids,
                    "moderator_id": int(user.discord_id),
                    "moderator_name": user.username,
                },
            ) as response:
                data = await response.json()
                
                if not response.ok:
                    error_message = data.get("detail", "Erreur lors de l'appel à l'API Hermes")
                    raise HTTPException(status_code=response.status, detail=error_message)
                
                return data
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur dans /api/moderation/bulk-delete-warns: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.get("/api/moderation/warns/{user_id}", response_class=JSONResponse)
async def get_user_warns_api(request: Request, user_id: str):
    """API pour récupérer les avertissements d'un utilisateur via le bot Hermes.

    Args:
        request: Objet Request FastAPI
        user_id: ID Discord de l'utilisateur

    Returns:
        JSON: Liste des avertissements de l'utilisateur
    """
    from app.database import get_db
    import os
    import aiohttp
    
    db = next(get_db())
    
    try:
        # Vérifier l'authentification
        user = get_current_user_dependency(request, db)
        logger.info(f"Récupération des warns pour l'utilisateur {user_id} par {user.username}")
        
        # Configuration de l'API Hermes
        hermes_api_url = os.getenv("HERMES_API_URL", "http://localhost:8001")
        hermes_api_token = os.getenv("HERMES_API_TOKEN")
        
        logger.info(f"HERMES_API_URL: {hermes_api_url}")
        logger.info(f"HERMES_API_TOKEN présent: {bool(hermes_api_token)}")
        
        if not hermes_api_token:
            logger.error("HERMES_API_TOKEN non configuré")
            raise HTTPException(
                status_code=500,
                detail="Configuration serveur manquante (HERMES_API_TOKEN)"
            )
        
        # Convertir user_id en int pour l'API Hermes (qui attend un int)
        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            logger.error(f"ID utilisateur invalide: {user_id}")
            raise HTTPException(status_code=400, detail="ID utilisateur invalide")
        
        # Appeler l'API Hermes
        logger.info(f"Appel de l'API Hermes: {hermes_api_url}/warns/{user_id_int}")
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{hermes_api_url}/warns/{user_id_int}",
                headers={
                    "Authorization": f"Bearer {hermes_api_token}",
                },
            ) as response:
                logger.info(f"Réponse de l'API Hermes: status={response.status}")
                if not response.ok:
                    if response.status == 404:
                        logger.info(f"Utilisateur {user_id_int} non trouvé ou aucun warn (404)")
                        # Pas d'avertissements ou utilisateur non trouvé
                        return {
                            "user_id": user_id_int,
                            "warn_count": 0,
                            "warns": []
                        }
                    error_data = await response.json()
                    error_message = error_data.get("detail", "Erreur lors de l'appel à l'API Hermes")
                    logger.error(f"Erreur de l'API Hermes: {error_message}")
                    raise HTTPException(status_code=response.status, detail=error_message)
                
                data = await response.json()
                logger.info(f"Warns récupérés: {data.get('warn_count', 0)} warns pour l'utilisateur {user_id_int}")
                logger.info(f"Structure des données: user_id={data.get('user_id')}, warn_count={data.get('warn_count')}, warns length={len(data.get('warns', []))}")
                if data.get('warns'):
                    logger.info(f"Premier warn: {data['warns'][0] if data['warns'] else 'None'}")
                return data
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur dans /api/moderation/warns/{user_id}: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.post("/api/moderation/warn", response_class=JSONResponse)
async def warn_user_api(request: Request):
    """API pour donner un avertissement via le bot Hermes.

    Args:
        request: Objet Request FastAPI

    Returns:
        JSON: Résultat de l'opération
    """
    from app.database import get_db
    from app.services.discord import discord_service
    import os
    import aiohttp
    
    db = next(get_db())
    
    try:
        # Vérifier l'authentification
        user = get_current_user_dependency(request, db)
        
        # Récupérer les données de la requête
        body = await request.json()
        username_or_id = body.get("username") or body.get("user_id")  # Support des deux formats
        reason = body.get("reason", "Aucune raison spécifiée")
        
        # Validation
        if not username_or_id:
            raise HTTPException(status_code=400, detail="username ou user_id est requis")
        
        # Déterminer si c'est un ID (numérique) ou un pseudo
        user_id = None
        
        # Si c'est déjà un entier, c'est un ID Discord
        if isinstance(username_or_id, int):
            user_id = username_or_id
        else:
            # Convertir en chaîne pour vérifier
            username_or_id_str = str(username_or_id)
            if username_or_id_str.isdigit():
                # C'est un ID Discord (envoyé comme chaîne)
                user_id = int(username_or_id_str)
            else:
                # C'est un pseudo, chercher l'utilisateur
                member = await discord_service.find_user_by_username(username_or_id_str)
                if not member:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Utilisateur '{username_or_id_str}' non trouvé sur le serveur Discord"
                    )
                user_id_str = member.get("user", {}).get("id")
                if not user_id_str:
                    raise HTTPException(
                        status_code=404,
                        detail=f"ID utilisateur non trouvé pour '{username_or_id_str}'"
                    )
                # Convertir en int mais logger pour vérifier
                user_id = int(user_id_str)
                logger.info(f"🔍 DEBUG warn_user_api: Utilisateur trouvé: {username_or_id_str} -> ID string={user_id_str}, ID int={user_id}")
        
        # Logs de débogage pour vérifier l'ID
        logger.info(f"🔍 DEBUG warn_user_api: user_id final={user_id} (type: {type(user_id)}), reason={reason}")
        logger.info(f"🔍 DEBUG warn_user_api: moderator_id={int(user.discord_id)}, moderator_name={user.username}")
        
        # Configuration de l'API Hermes
        hermes_api_url = os.getenv("HERMES_API_URL", "http://localhost:8001")
        hermes_api_token = os.getenv("HERMES_API_TOKEN")
        
        if not hermes_api_token:
            raise HTTPException(
                status_code=500,
                detail="Configuration serveur manquante (HERMES_API_TOKEN)"
            )
        
        # Préparer le payload JSON
        payload = {
            "user_id": user_id,
            "reason": reason,
            "moderator_id": int(user.discord_id),
            "moderator_name": user.username,
        }
        logger.info(f"🔍 DEBUG warn_user_api: Payload envoyé à Hermes: {payload}")
        
        # Appeler l'API Hermes
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{hermes_api_url}/warn",
                headers={
                    "Authorization": f"Bearer {hermes_api_token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            ) as response:
                data = await response.json()
                
                if not response.ok:
                    error_message = data.get("detail", "Erreur lors de l'appel à l'API Hermes")
                    raise HTTPException(status_code=response.status, detail=error_message)
                
                return data
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur dans /api/moderation/warn: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.post("/api/moderation/kick", response_class=JSONResponse)
async def kick_user_api(request: Request):
    """API pour expulser un utilisateur via le bot Hermes."""
    from app.database import get_db
    import os
    import aiohttp
    
    db = next(get_db())
    
    try:
        user = get_current_user_dependency(request, db)
        body = await request.json()
        user_id = body.get("user_id")
        reason = body.get("reason", "Aucune raison spécifiée")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id est requis")
        
        hermes_api_url = os.getenv("HERMES_API_URL", "http://localhost:8001")
        hermes_api_token = os.getenv("HERMES_API_TOKEN")
        
        if not hermes_api_token:
            raise HTTPException(status_code=500, detail="Configuration serveur manquante (HERMES_API_TOKEN)")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{hermes_api_url}/kick",
                headers={
                    "Authorization": f"Bearer {hermes_api_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "user_id": int(user_id),
                    "reason": reason,
                    "moderator_id": int(user.discord_id),
                    "moderator_name": user.username,
                },
            ) as response:
                data = await response.json()
                if not response.ok:
                    error_message = data.get("detail", "Erreur lors de l'appel à l'API Hermes")
                    raise HTTPException(status_code=response.status, detail=error_message)
                return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur dans /api/moderation/kick: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.post("/api/moderation/ban", response_class=JSONResponse)
async def ban_user_api(request: Request):
    """API pour bannir un utilisateur via le bot Hermes."""
    from app.database import get_db
    import os
    import aiohttp
    
    db = next(get_db())
    
    try:
        user = get_current_user_dependency(request, db)
        body = await request.json()
        user_id = body.get("user_id")
        reason = body.get("reason", "Aucune raison spécifiée")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id est requis")
        
        hermes_api_url = os.getenv("HERMES_API_URL", "http://localhost:8001")
        hermes_api_token = os.getenv("HERMES_API_TOKEN")
        
        if not hermes_api_token:
            raise HTTPException(status_code=500, detail="Configuration serveur manquante (HERMES_API_TOKEN)")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{hermes_api_url}/ban",
                headers={
                    "Authorization": f"Bearer {hermes_api_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "user_id": int(user_id),
                    "reason": reason,
                    "moderator_id": int(user.discord_id),
                    "moderator_name": user.username,
                },
            ) as response:
                data = await response.json()
                if not response.ok:
                    error_message = data.get("detail", "Erreur lors de l'appel à l'API Hermes")
                    raise HTTPException(status_code=response.status, detail=error_message)
                return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur dans /api/moderation/ban: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.post("/api/moderation/mute", response_class=JSONResponse)
async def mute_user_api(request: Request):
    """API pour muter un utilisateur via le bot Hermes."""
    from app.database import get_db
    import os
    import aiohttp
    
    db = next(get_db())
    
    try:
        user = get_current_user_dependency(request, db)
        body = await request.json()
        user_id = body.get("user_id")
        reason = body.get("reason", "Aucune raison spécifiée")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id est requis")
        
        hermes_api_url = os.getenv("HERMES_API_URL", "http://localhost:8001")
        hermes_api_token = os.getenv("HERMES_API_TOKEN")
        
        if not hermes_api_token:
            raise HTTPException(status_code=500, detail="Configuration serveur manquante (HERMES_API_TOKEN)")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{hermes_api_url}/mute",
                headers={
                    "Authorization": f"Bearer {hermes_api_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "user_id": int(user_id),
                    "reason": reason,
                    "moderator_id": int(user.discord_id),
                    "moderator_name": user.username,
                },
            ) as response:
                data = await response.json()
                if not response.ok:
                    error_message = data.get("detail", "Erreur lors de l'appel à l'API Hermes")
                    raise HTTPException(status_code=response.status, detail=error_message)
                return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur dans /api/moderation/mute: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.post("/api/moderation/unmute", response_class=JSONResponse)
async def unmute_user_api(request: Request):
    """API pour unmuter un utilisateur via le bot Hermes."""
    from app.database import get_db
    import os
    import aiohttp
    
    db = next(get_db())
    
    try:
        user = get_current_user_dependency(request, db)
        body = await request.json()
        user_id = body.get("user_id")
        reason = body.get("reason", "Unmute via interface web")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id est requis")
        
        hermes_api_url = os.getenv("HERMES_API_URL", "http://localhost:8001")
        hermes_api_token = os.getenv("HERMES_API_TOKEN")
        
        if not hermes_api_token:
            raise HTTPException(status_code=500, detail="Configuration serveur manquante (HERMES_API_TOKEN)")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{hermes_api_url}/unmute",
                headers={
                    "Authorization": f"Bearer {hermes_api_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "user_id": int(user_id),
                    "reason": reason,
                    "moderator_id": int(user.discord_id),
                    "moderator_name": user.username,
                },
            ) as response:
                data = await response.json()
                if not response.ok:
                    error_message = data.get("detail", "Erreur lors de l'appel à l'API Hermes")
                    raise HTTPException(status_code=response.status, detail=error_message)
                return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur dans /api/moderation/unmute: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.post("/api/moderation/tempban", response_class=JSONResponse)
async def tempban_user_api(request: Request):
    """API pour bannir temporairement un utilisateur via le bot Hermes."""
    from app.database import get_db
    import os
    import aiohttp
    
    db = next(get_db())
    
    try:
        user = get_current_user_dependency(request, db)
        body = await request.json()
        user_id = body.get("user_id")
        duration = body.get("duration")
        unit = body.get("unit")
        reason = body.get("reason", "Aucune raison spécifiée")
        
        if not user_id or not duration or not unit:
            raise HTTPException(status_code=400, detail="user_id, duration et unit sont requis")
        
        hermes_api_url = os.getenv("HERMES_API_URL", "http://localhost:8001")
        hermes_api_token = os.getenv("HERMES_API_TOKEN")
        
        if not hermes_api_token:
            raise HTTPException(status_code=500, detail="Configuration serveur manquante (HERMES_API_TOKEN)")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{hermes_api_url}/tempban",
                headers={
                    "Authorization": f"Bearer {hermes_api_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "user_id": int(user_id),
                    "duration": int(duration),
                    "unit": unit,
                    "reason": reason,
                    "moderator_id": int(user.discord_id),
                    "moderator_name": user.username,
                },
            ) as response:
                data = await response.json()
                if not response.ok:
                    error_message = data.get("detail", "Erreur lors de l'appel à l'API Hermes")
                    raise HTTPException(status_code=response.status, detail=error_message)
                return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur dans /api/moderation/tempban: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.post("/api/moderation/tempmute", response_class=JSONResponse)
async def tempmute_user_api(request: Request):
    """API pour muter temporairement un utilisateur via le bot Hermes."""
    from app.database import get_db
    import os
    import aiohttp
    
    db = next(get_db())
    
    try:
        user = get_current_user_dependency(request, db)
        body = await request.json()
        user_id = body.get("user_id")
        duration = body.get("duration")
        unit = body.get("unit")
        reason = body.get("reason", "Aucune raison spécifiée")
        
        if not user_id or not duration or not unit:
            raise HTTPException(status_code=400, detail="user_id, duration et unit sont requis")
        
        hermes_api_url = os.getenv("HERMES_API_URL", "http://localhost:8001")
        hermes_api_token = os.getenv("HERMES_API_TOKEN")
        
        if not hermes_api_token:
            raise HTTPException(status_code=500, detail="Configuration serveur manquante (HERMES_API_TOKEN)")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{hermes_api_url}/tempmute",
                headers={
                    "Authorization": f"Bearer {hermes_api_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "user_id": int(user_id),
                    "duration": int(duration),
                    "unit": unit,
                    "reason": reason,
                    "moderator_id": int(user.discord_id),
                    "moderator_name": user.username,
                },
            ) as response:
                data = await response.json()
                if not response.ok:
                    error_message = data.get("detail", "Erreur lors de l'appel à l'API Hermes")
                    raise HTTPException(status_code=response.status, detail=error_message)
                return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur dans /api/moderation/tempmute: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.get("/health")
async def health():
    """Endpoint de santé simple pour vérifier que l'API est opérationnelle.

    Returns:
        dict: Statut simple de l'API
    """
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics(request: Request):
    """Endpoint pour exporter les métriques au format Prometheus (pour Grafana).

    Args:
        request: Objet Request FastAPI

    Returns:
        str: Métriques au format Prometheus
    """
    from app.database import get_db
    from app.services.config_service import config_service
    from app.services.metrics_service import metrics_service

    # Utiliser le générateur correctement pour fermer la session automatiquement
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # Vérifier si les métriques sont activées
        if not config_service.is_metrics_enabled(db):
            raise HTTPException(status_code=403, detail="Metrics are disabled")
        
        return metrics_service.get_prometheus_metrics(db)
    finally:
        # Fermer la session explicitement
        db.close()

