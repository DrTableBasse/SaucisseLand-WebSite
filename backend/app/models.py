"""Modèles SQLAlchemy pour la base de données."""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

# Table de liaison many-to-many entre Article et Tag
article_tags = Table(
    'article_tags',
    Base.metadata,
    Column('article_id', Integer, ForeignKey('articles.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True),
)


class User(Base):
    """Modèle utilisateur Discord."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    discord_id = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, nullable=False)
    discriminator = Column(String)
    avatar = Column(String)
    email = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    articles = relationship("Article", back_populates="author")


class Article(Base):
    """Modèle article de blog."""

    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    slug = Column(String, unique=True, index=True, nullable=False)
    content = Column(Text, nullable=False)  # Markdown content
    excerpt = Column(Text)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    published = Column(Boolean, default=False)
    views = Column(Integer, default=0, nullable=False)
    likes = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    author = relationship("User", back_populates="articles")
    images = relationship("ArticleImage", back_populates="article")
    likes_rel = relationship("ArticleLike", back_populates="article", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=article_tags, back_populates="articles")


class ArticleImage(Base):
    """Modèle image associée à un article.

    L'image peut être uploadée avant la création de l'article (article_id peut être None).
    Elle sera associée à l'article lors de sa création.
    """

    __tablename__ = "article_images"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=True)  # Optionnel pour upload avant création
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    mime_type = Column(String)
    file_size = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    article = relationship("Article", back_populates="images")


class ArticleLike(Base):
    """Modèle pour les likes d'articles par utilisateur."""

    __tablename__ = "article_likes"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    article = relationship("Article", back_populates="likes_rel")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint('article_id', 'user_id', name='unique_article_user_like'),
    )


class Tag(Base):
    """Modèle tag pour les articles."""

    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    slug = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text)
    color = Column(String, default="#3b82f6")  # Couleur par défaut (bleu)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    articles = relationship("Article", secondary=article_tags, back_populates="tags")


class AppConfig(Base):
    """Modèle pour les configurations dynamiques de l'application."""

    __tablename__ = "app_configs"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    description = Column(Text)
    category = Column(String, default="general")  # general, metrics, security, etc.
    is_sensitive = Column(Boolean, default=False)  # Masquer la valeur dans l'interface
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    updater = relationship("User")

