"""Schémas Pydantic pour la validation des données."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """Schéma de base pour un utilisateur."""

    discord_id: str
    username: str
    discriminator: Optional[str] = None
    avatar: Optional[str] = None
    email: Optional[EmailStr] = None


class UserCreate(UserBase):
    """Schéma pour la création d'un utilisateur."""

    pass


class UserResponse(UserBase):
    """Schéma de réponse pour un utilisateur."""

    id: int
    created_at: datetime

    class Config:
        """Configuration Pydantic."""

        from_attributes = True


class ArticleBase(BaseModel):
    """Schéma de base pour un article."""

    title: str
    slug: Optional[str] = None
    content: str
    excerpt: Optional[str] = None
    published: bool = False


class ArticleCreate(ArticleBase):
    """Schéma pour la création d'un article."""

    tag_ids: Optional[List[int]] = []


class ArticleUpdate(BaseModel):
    """Schéma pour la mise à jour d'un article."""

    title: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    published: Optional[bool] = None
    tag_ids: Optional[List[int]] = None


class ArticleResponse(BaseModel):
    """Schéma de réponse pour un article complet."""

    id: int
    title: str
    slug: str
    content: str
    excerpt: Optional[str] = None
    published: bool
    views: int
    likes: int
    author_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    author: UserResponse
    tags: List["TagResponse"] = []

    class Config:
        """Configuration Pydantic."""

        from_attributes = True


class ArticleListResponse(BaseModel):
    """Schéma de réponse pour la liste d'articles."""

    id: int
    title: str
    slug: str
    excerpt: Optional[str] = None
    published: bool
    views: int
    likes: int
    author: UserResponse
    created_at: datetime
    tags: List["TagResponse"] = []

    class Config:
        """Configuration Pydantic."""

        from_attributes = True


class ImageResponse(BaseModel):
    """Schéma de réponse pour une image."""

    id: int
    filename: str
    original_filename: str
    file_path: str
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    created_at: datetime

    class Config:
        """Configuration Pydantic."""

        from_attributes = True


class TagBase(BaseModel):
    """Schéma de base pour un tag."""

    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = "#3b82f6"


class TagCreate(TagBase):
    """Schéma pour la création d'un tag."""

    pass


class TagUpdate(BaseModel):
    """Schéma pour la mise à jour d'un tag."""

    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None


class TagResponse(TagBase):
    """Schéma de réponse pour un tag."""

    id: int
    created_at: datetime

    class Config:
        """Configuration Pydantic."""

        from_attributes = True


class AppConfigBase(BaseModel):
    """Schéma de base pour une configuration."""

    key: str
    value: str
    description: Optional[str] = None
    category: str = "general"
    is_sensitive: bool = False


class AppConfigCreate(AppConfigBase):
    """Schéma pour la création d'une configuration."""

    pass


class AppConfigUpdate(BaseModel):
    """Schéma pour la mise à jour d'une configuration."""

    value: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    is_sensitive: Optional[bool] = None


class AppConfigResponse(AppConfigBase):
    """Schéma de réponse pour une configuration."""

    id: int
    updated_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        """Configuration Pydantic."""

        from_attributes = True


class HealthMetricsResponse(BaseModel):
    """Schéma de réponse pour les métriques de santé."""

    status: str
    timestamp: datetime
    database: dict
    application: dict
    metrics_enabled: bool


class MetricsToggleRequest(BaseModel):
    """Schéma pour activer/désactiver les métriques."""

    enabled: bool


# Reconstruire les modèles qui utilisent des références forward
ArticleResponse.model_rebuild()
ArticleListResponse.model_rebuild()

