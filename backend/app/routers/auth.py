from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import UserResponse
from app.services.discord import discord_service
from app.config import settings
import secrets
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

router = APIRouter()

# Stockage temporaire des sessions (en production, utiliser Redis ou une DB)
sessions = {}

@router.get("/login")
async def login():
    """Redirige vers Discord OAuth"""
    redirect_uri = settings.DISCORD_REDIRECT_URI_FINAL
    discord_oauth_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={settings.DISCORD_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope=identify email guilds"
    )
    logger.info(f"Redirection vers Discord OAuth avec redirect_uri: {redirect_uri}")
    return RedirectResponse(url=discord_oauth_url)

@router.get("/callback/social/discord")
async def callback(code: str, request: Request, db: Session = Depends(get_db)):
    """Callback OAuth Discord"""
    try:
        logger.info(f"Callback Discord reçu avec code: {code[:10]}...")
        
        # Échanger le code contre un token
        token_data = await discord_service.exchange_code_for_token(code)
        logger.debug(f"Réponse token exchange: {list(token_data.keys())}")
        
        if "access_token" not in token_data:
            error_detail = token_data.get("error_description", token_data.get("error", "Unknown error"))
            logger.error(f"Échec de l'échange du code: {error_detail}")
            raise HTTPException(status_code=400, detail=f"Failed to get access token: {error_detail}")
        
        access_token = token_data["access_token"]
        logger.info("Token d'accès obtenu avec succès")
        
        # Récupérer les infos utilisateur
        user_info = await discord_service.get_user_info(access_token)
        if "id" not in user_info:
            logger.error(f"Informations utilisateur invalides: {user_info}")
            raise HTTPException(status_code=400, detail="Failed to get user info from Discord")
        
        discord_id = str(user_info["id"])
        logger.info(f"Informations utilisateur récupérées pour Discord ID: {discord_id}")
        
        # Vérifier ou créer l'utilisateur
        user = db.query(User).filter(User.discord_id == discord_id).first()
        if not user:
            logger.info(f"Création d'un nouvel utilisateur: {user_info.get('username')}")
            user = User(
                discord_id=discord_id,
                username=user_info.get("username", ""),
                discriminator=user_info.get("discriminator"),
                avatar=user_info.get("avatar"),
                email=user_info.get("email")
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            logger.info(f"Mise à jour de l'utilisateur existant: {user.username}")
            # Mettre à jour les infos
            user.username = user_info.get("username", user.username)
            user.avatar = user_info.get("avatar", user.avatar)
            user.email = user_info.get("email", user.email)
            db.commit()
        
        # Créer une session
        session_token = secrets.token_urlsafe(32)
        sessions[session_token] = {
            "user_id": user.id,
            "discord_id": discord_id,
            "expires_at": datetime.now() + timedelta(days=7)
        }
        logger.info(f"Session créée pour l'utilisateur {user.id}")
        
        # Rediriger avec le cookie de session
        response = RedirectResponse(url="/")
        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=session_token,
            httponly=True,
            max_age=7*24*60*60,
            samesite="lax"
        )
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Erreur dans le callback Discord: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/logout")
@router.post("/logout")
async def logout(request: Request):
    """Déconnexion"""
    session_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if session_token and session_token in sessions:
        del sessions[session_token]
    
    # Rediriger vers la page d'accueil après déconnexion
    response = RedirectResponse(url="/")
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        httponly=True,
        samesite="lax"
    )
    return response

@router.get("/me", response_model=UserResponse)
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Récupère l'utilisateur actuel"""
    session_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not session_token or session_token not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session_data = sessions[session_token]
    if datetime.now() > session_data["expires_at"]:
        del sessions[session_token]
        raise HTTPException(status_code=401, detail="Session expired")
    
    user = db.query(User).filter(User.id == session_data["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

@router.get("/permissions")
async def check_permissions(request: Request, db: Session = Depends(get_db)):
    """Vérifie si l'utilisateur a les permissions pour créer des articles"""
    try:
        user = get_current_user_dependency(request, db)
        has_permission = await discord_service.check_user_has_allowed_role(user.discord_id)
        return {"can_create_articles": has_permission}
    except:
        return {"can_create_articles": False}

@router.get("/debug/roles")
async def debug_roles(request: Request, db: Session = Depends(get_db)):
    """Endpoint de debug pour voir les rôles de l'utilisateur"""
    try:
        user = get_current_user_dependency(request, db)
        user_roles = await discord_service.get_user_roles(user.discord_id)
        allowed_roles = settings.ALLOWED_ROLE_IDS
        has_permission = await discord_service.check_user_has_allowed_role(user.discord_id)
        
        return {
            "user_id": user.discord_id,
            "username": user.username,
            "user_roles": user_roles,
            "allowed_roles": allowed_roles,
            "has_permission": has_permission,
            "message": "Vérifiez que votre rôle est dans ALLOWED_ROLE_IDS du fichier .env"
        }
    except Exception as e:
        return {
            "error": str(e),
            "message": "Vous devez être connecté pour voir vos rôles"
        }

def get_current_user_dependency(request: Request, db: Session = Depends(get_db)) -> User:
    """Dependency pour obtenir l'utilisateur actuel"""
    session_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not session_token or session_token not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session_data = sessions[session_token]
    if datetime.now() > session_data["expires_at"]:
        del sessions[session_token]
        raise HTTPException(status_code=401, detail="Session expired")
    
    user = db.query(User).filter(User.id == session_data["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

