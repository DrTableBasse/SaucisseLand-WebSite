from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from app.database import engine, Base
from app.routers import auth, articles, images
from app.config import settings
from app.routers.auth import get_current_user_dependency
from app.models import User
import time
import logging
import aiohttp

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Attendre que la base de données soit prête
def init_db():
    max_retries = 30
    retry_count = 0
    while retry_count < max_retries:
        try:
            # Tester la connexion
            with engine.connect() as conn:
                from sqlalchemy import text
                conn.execute(text("SELECT 1"))
                logger.info("Connexion à la base de données réussie")
                break
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                logger.error(f"Impossible de se connecter à la base de données après {max_retries} tentatives: {e}")
                # Ne pas bloquer le démarrage, on réessayera plus tard
                return
            logger.info(f"Tentative de connexion {retry_count}/{max_retries}...")
            time.sleep(2)
    
    # Créer les tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tables créées avec succès")
    except Exception as e:
        logger.error(f"Erreur lors de la création des tables: {e}")
        # Ne pas bloquer le démarrage

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Au démarrage
    logger.info("Initialisation de l'application...")
    init_db()
    yield
    # À l'arrêt
    logger.info("Arrêt de l'application...")

app = FastAPI(title="Discord Auth Blog", version="1.0.0", lifespan=lifespan)

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

async def get_user_and_permissions(request: Request):
    """Helper pour obtenir l'utilisateur et ses permissions"""
    user = None
    can_create_articles = False
    try:
        from app.database import get_db
        from app.services.discord import discord_service
        db = next(get_db())
        user = get_current_user_dependency(request, db)
        if user:
            can_create_articles = await discord_service.check_user_has_allowed_role(user.discord_id)
    except:
        pass
    return user, can_create_articles

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    user, can_create_articles = await get_user_and_permissions(request)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "can_create_articles": can_create_articles
    })

@app.get("/create", response_class=HTMLResponse)
async def create_page(request: Request):
    from app.database import get_db
    from app.services.discord import discord_service
    db = next(get_db())
    try:
        user = get_current_user_dependency(request, db)
        can_create_articles = await discord_service.check_user_has_allowed_role(user.discord_id)
        if not can_create_articles:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": "Vous n'avez pas les permissions nécessaires pour créer des articles. Vous devez avoir un des rôles Discord autorisés."
            })
    except:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Vous devez être connecté pour créer un article"
        })
    return templates.TemplateResponse("create.html", {
        "request": request,
        "user": user,
        "can_create_articles": True
    })

@app.get("/article/{slug}", response_class=HTMLResponse)
async def article_page(slug: str, request: Request):
    from app.database import get_db
    from app.models import Article
    db = next(get_db())
    article = db.query(Article).filter(Article.slug == slug).first()
    if not article:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Article non trouvé"
        })
    
    # Vérifier si l'article est publié ou si l'utilisateur est l'auteur
    user, can_create_articles = await get_user_and_permissions(request)
    is_author = False
    if user:
        is_author = user.id == article.author_id
    
    if not article.published and not is_author:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Cet article n'est pas publié"
        })
    return templates.TemplateResponse("article.html", {
        "request": request,
        "article": article,
        "user": user,
        "can_create_articles": can_create_articles
    })

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
    return {"status": "ok"}

