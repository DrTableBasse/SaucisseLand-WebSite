"""Service de collecte de métriques pour Grafana."""
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.models import Article, ArticleImage, ArticleLike, Tag, User

logger = logging.getLogger(__name__)


class MetricsService:
    """Service pour collecter des métriques de l'application."""

    def __init__(self):
        """Initialise le service de métriques."""
        self.start_time = time.time()

    def get_uptime(self) -> float:
        """Calcule le temps de fonctionnement depuis le démarrage.

        Returns:
            float: Temps de fonctionnement en secondes
        """
        return time.time() - self.start_time

    def collect_database_metrics(self, db: Session) -> Dict:
        """Collecte les métriques de la base de données.

        Args:
            db: Session de base de données

        Returns:
            dict: Dictionnaire contenant les métriques de la base de données
        """
        try:
            # Test de connexion avec mesure du temps
            start = time.time()
            db.execute(text("SELECT 1"))
            db_latency = (time.time() - start) * 1000  # en millisecondes
            db_status = "connected"
        except Exception as e:
            logger.error(f"Erreur de connexion à la base de données: {e}")
            db_status = "disconnected"
            db_latency = 0

        # Dates pour les métriques temporelles
        now = datetime.utcnow()
        last_24h = now - timedelta(days=1)
        last_7d = now - timedelta(days=7)
        last_30d = now - timedelta(days=30)

        # Compter les utilisateurs
        users_count = db.query(func.count(User.id)).scalar() or 0
        users_new_24h = db.query(func.count(User.id)).filter(User.created_at >= last_24h).scalar() or 0
        users_new_7d = db.query(func.count(User.id)).filter(User.created_at >= last_7d).scalar() or 0
        users_new_30d = db.query(func.count(User.id)).filter(User.created_at >= last_30d).scalar() or 0

        # Compter les articles
        articles_total = db.query(func.count(Article.id)).scalar() or 0
        articles_published = db.query(func.count(Article.id)).filter(Article.published == True).scalar() or 0
        articles_draft = articles_total - articles_published
        articles_new_24h = db.query(func.count(Article.id)).filter(Article.created_at >= last_24h).scalar() or 0
        articles_new_7d = db.query(func.count(Article.id)).filter(Article.created_at >= last_7d).scalar() or 0
        articles_new_30d = db.query(func.count(Article.id)).filter(Article.created_at >= last_30d).scalar() or 0

        # Compter les likes
        likes_total = db.query(func.count(ArticleLike.id)).scalar() or 0
        likes_new_24h = db.query(func.count(ArticleLike.id)).filter(ArticleLike.created_at >= last_24h).scalar() or 0
        likes_new_7d = db.query(func.count(ArticleLike.id)).filter(ArticleLike.created_at >= last_7d).scalar() or 0

        # Compter les vues totales
        views_total = db.query(func.sum(Article.views)).scalar() or 0

        # Compter les tags
        tags_count = db.query(func.count(Tag.id)).scalar() or 0

        # Articles les plus populaires (top 5)
        top_articles = (
            db.query(Article.id, Article.title, Article.views, Article.likes)
            .order_by(Article.views.desc())
            .limit(5)
            .all()
        )
        top_articles_list = [
            {"id": a.id, "title": a.title, "views": a.views, "likes": a.likes}
            for a in top_articles
        ]

        # Articles les plus aimés (top 5)
        top_liked_articles = (
            db.query(Article.id, Article.title, Article.views, Article.likes)
            .order_by(Article.likes.desc())
            .limit(5)
            .all()
        )
        top_liked_list = [
            {"id": a.id, "title": a.title, "views": a.views, "likes": a.likes}
            for a in top_liked_articles
        ]

        # Tags les plus utilisés (top 10)
        from app.models import article_tags
        top_tags = (
            db.query(Tag.id, Tag.name, func.count(article_tags.c.article_id).label('usage_count'))
            .join(article_tags)
            .group_by(Tag.id, Tag.name)
            .order_by(func.count(article_tags.c.article_id).desc())
            .limit(10)
            .all()
        )
        top_tags_list = [
            {"id": t.id, "name": t.name, "usage_count": t.usage_count}
            for t in top_tags
        ]

        # Auteurs les plus actifs (top 5)
        top_authors = (
            db.query(
                User.id,
                User.username,
                func.count(Article.id).label('articles_count')
            )
            .join(Article)
            .group_by(User.id, User.username)
            .order_by(func.count(Article.id).desc())
            .limit(5)
            .all()
        )
        top_authors_list = [
            {"id": a.id, "username": a.username, "articles_count": a.articles_count}
            for a in top_authors
        ]

        # Compter les images
        images_count = db.query(func.count(ArticleImage.id)).scalar() or 0
        images_size_total = db.query(func.sum(ArticleImage.file_size)).scalar() or 0

        # Calculer les ratios d'engagement
        engagement_rate = 0
        if views_total > 0:
            engagement_rate = round((likes_total / views_total) * 100, 2)

        return {
            "status": db_status,
            "latency_ms": round(db_latency, 2),
            "users": {
                "total": users_count,
                "new_24h": users_new_24h,
                "new_7d": users_new_7d,
                "new_30d": users_new_30d,
            },
            "articles": {
                "total": articles_total,
                "published": articles_published,
                "draft": articles_draft,
                "new_24h": articles_new_24h,
                "new_7d": articles_new_7d,
                "new_30d": articles_new_30d,
            },
            "engagement": {
                "total_likes": likes_total,
                "total_views": int(views_total),
                "likes_new_24h": likes_new_24h,
                "likes_new_7d": likes_new_7d,
                "average_views_per_article": round(views_total / articles_published, 2) if articles_published > 0 else 0,
                "average_likes_per_article": round(likes_total / articles_published, 2) if articles_published > 0 else 0,
                "engagement_rate_percent": engagement_rate,
                "likes_per_view_ratio": round(likes_total / views_total, 4) if views_total > 0 else 0,
            },
            "tags": {
                "total": tags_count,
                "top_tags": top_tags_list,
            },
            "content": {
                "top_articles_by_views": top_articles_list,
                "top_articles_by_likes": top_liked_list,
                "top_authors": top_authors_list,
            },
            "resources": {
                "images_total": images_count,
                "images_size_total_bytes": int(images_size_total) if images_size_total else 0,
                "images_size_total_mb": round((images_size_total or 0) / (1024 * 1024), 2),
            },
        }

    def collect_application_metrics(self) -> Dict:
        """Collecte les métriques de l'application.

        Returns:
            dict: Dictionnaire contenant les métriques de l'application
        """
        uptime_seconds = self.get_uptime()
        uptime_hours = uptime_seconds / 3600
        uptime_days = uptime_hours / 24

        # Métriques système (si psutil est disponible)
        system_metrics = {}
        try:
            import psutil
            process = psutil.Process()
            system_metrics = {
                "cpu_percent": round(process.cpu_percent(interval=0.1), 2),
                "memory_mb": round(process.memory_info().rss / (1024 * 1024), 2),
                "memory_percent": round(process.memory_percent(), 2),
            }
            
            # Métriques système globales
            system_metrics.update({
                "system_cpu_percent": round(psutil.cpu_percent(interval=0.1), 2),
                "system_memory_total_mb": round(psutil.virtual_memory().total / (1024 * 1024), 2),
                "system_memory_available_mb": round(psutil.virtual_memory().available / (1024 * 1024), 2),
                "system_memory_percent": round(psutil.virtual_memory().percent, 2),
            })
        except ImportError:
            # psutil n'est pas installé, on ignore
            pass
        except Exception as e:
            logger.warning(f"Impossible de collecter les métriques système: {e}")

        return {
            "uptime": {
                "seconds": round(uptime_seconds, 2),
                "hours": round(uptime_hours, 2),
                "days": round(uptime_days, 2),
            },
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "system": system_metrics,
        }

    def get_prometheus_metrics(self, db: Session) -> str:
        """Génère des métriques au format Prometheus.

        Args:
            db: Session de base de données

        Returns:
            str: Métriques au format Prometheus
        """
        db_metrics = self.collect_database_metrics(db)
        app_metrics = self.collect_application_metrics()

        lines = [
            "# HELP app_uptime_seconds Temps de fonctionnement de l'application en secondes",
            "# TYPE app_uptime_seconds gauge",
            f"app_uptime_seconds {app_metrics['uptime']['seconds']}",
            "",
            "# HELP app_database_status Statut de la base de données (1=connecté, 0=déconnecté)",
            "# TYPE app_database_status gauge",
            f"app_database_status {1 if db_metrics['status'] == 'connected' else 0}",
            "",
            "# HELP app_database_latency_ms Latence de la base de données en millisecondes",
            "# TYPE app_database_latency_ms gauge",
            f"app_database_latency_ms {db_metrics['latency_ms']}",
            "",
            "# HELP app_users_total Nombre total d'utilisateurs",
            "# TYPE app_users_total gauge",
            f"app_users_total {db_metrics['users']['total']}",
            "",
            "# HELP app_users_new_24h Nombre de nouveaux utilisateurs dans les 24 dernières heures",
            "# TYPE app_users_new_24h gauge",
            f"app_users_new_24h {db_metrics['users']['new_24h']}",
            "",
            "# HELP app_users_new_7d Nombre de nouveaux utilisateurs dans les 7 derniers jours",
            "# TYPE app_users_new_7d gauge",
            f"app_users_new_7d {db_metrics['users']['new_7d']}",
            "",
            "# HELP app_users_new_30d Nombre de nouveaux utilisateurs dans les 30 derniers jours",
            "# TYPE app_users_new_30d gauge",
            f"app_users_new_30d {db_metrics['users']['new_30d']}",
            "",
            "# HELP app_articles_total Nombre total d'articles",
            "# TYPE app_articles_total gauge",
            f"app_articles_total {db_metrics['articles']['total']}",
            "",
            "# HELP app_articles_published Nombre d'articles publiés",
            "# TYPE app_articles_published gauge",
            f"app_articles_published {db_metrics['articles']['published']}",
            "",
            "# HELP app_articles_draft Nombre d'articles en brouillon",
            "# TYPE app_articles_draft gauge",
            f"app_articles_draft {db_metrics['articles']['draft']}",
            "",
            "# HELP app_articles_new_24h Nombre de nouveaux articles dans les 24 dernières heures",
            "# TYPE app_articles_new_24h gauge",
            f"app_articles_new_24h {db_metrics['articles']['new_24h']}",
            "",
            "# HELP app_articles_new_7d Nombre de nouveaux articles dans les 7 derniers jours",
            "# TYPE app_articles_new_7d gauge",
            f"app_articles_new_7d {db_metrics['articles']['new_7d']}",
            "",
            "# HELP app_articles_new_30d Nombre de nouveaux articles dans les 30 derniers jours",
            "# TYPE app_articles_new_30d gauge",
            f"app_articles_new_30d {db_metrics['articles']['new_30d']}",
            "",
            "# HELP app_likes_total Nombre total de likes",
            "# TYPE app_likes_total gauge",
            f"app_likes_total {db_metrics['engagement']['total_likes']}",
            "",
            "# HELP app_likes_new_24h Nombre de nouveaux likes dans les 24 dernières heures",
            "# TYPE app_likes_new_24h gauge",
            f"app_likes_new_24h {db_metrics['engagement']['likes_new_24h']}",
            "",
            "# HELP app_likes_new_7d Nombre de nouveaux likes dans les 7 derniers jours",
            "# TYPE app_likes_new_7d gauge",
            f"app_likes_new_7d {db_metrics['engagement']['likes_new_7d']}",
            "",
            "# HELP app_views_total Nombre total de vues",
            "# TYPE app_views_total gauge",
            f"app_views_total {db_metrics['engagement']['total_views']}",
            "",
            "# HELP app_engagement_rate_percent Taux d'engagement (likes/vues * 100)",
            "# TYPE app_engagement_rate_percent gauge",
            f"app_engagement_rate_percent {db_metrics['engagement']['engagement_rate_percent']}",
            "",
            "# HELP app_avg_views_per_article Nombre moyen de vues par article",
            "# TYPE app_avg_views_per_article gauge",
            f"app_avg_views_per_article {db_metrics['engagement']['average_views_per_article']}",
            "",
            "# HELP app_avg_likes_per_article Nombre moyen de likes par article",
            "# TYPE app_avg_likes_per_article gauge",
            f"app_avg_likes_per_article {db_metrics['engagement']['average_likes_per_article']}",
            "",
            "# HELP app_tags_total Nombre total de tags",
            "# TYPE app_tags_total gauge",
            f"app_tags_total {db_metrics['tags']['total']}",
            "",
            "# HELP app_images_total Nombre total d'images uploadées",
            "# TYPE app_images_total gauge",
            f"app_images_total {db_metrics['resources']['images_total']}",
            "",
            "# HELP app_images_size_total_bytes Taille totale des images en octets",
            "# TYPE app_images_size_total_bytes gauge",
            f"app_images_size_total_bytes {db_metrics['resources']['images_size_total_bytes']}",
            "",
            "# HELP app_images_size_total_mb Taille totale des images en mégaoctets",
            "# TYPE app_images_size_total_mb gauge",
            f"app_images_size_total_mb {db_metrics['resources']['images_size_total_mb']}",
        ]

        # Ajouter les métriques système si disponibles
        if app_metrics.get('system'):
            system = app_metrics['system']
            if 'cpu_percent' in system:
                lines.extend([
                    "",
                    "# HELP app_process_cpu_percent Pourcentage CPU utilisé par le processus",
                    "# TYPE app_process_cpu_percent gauge",
                    f"app_process_cpu_percent {system['cpu_percent']}",
                    "",
                    "# HELP app_process_memory_mb Mémoire utilisée par le processus en MB",
                    "# TYPE app_process_memory_mb gauge",
                    f"app_process_memory_mb {system['memory_mb']}",
                    "",
                    "# HELP app_process_memory_percent Pourcentage de mémoire utilisée par le processus",
                    "# TYPE app_process_memory_percent gauge",
                    f"app_process_memory_percent {system['memory_percent']}",
                ])
            
            if 'system_cpu_percent' in system:
                lines.extend([
                    "",
                    "# HELP app_system_cpu_percent Pourcentage CPU système",
                    "# TYPE app_system_cpu_percent gauge",
                    f"app_system_cpu_percent {system['system_cpu_percent']}",
                    "",
                    "# HELP app_system_memory_percent Pourcentage de mémoire système utilisée",
                    "# TYPE app_system_memory_percent gauge",
                    f"app_system_memory_percent {system['system_memory_percent']}",
                    "",
                    "# HELP app_system_memory_available_mb Mémoire système disponible en MB",
                    "# TYPE app_system_memory_available_mb gauge",
                    f"app_system_memory_available_mb {system['system_memory_available_mb']}",
                ])

        return "\n".join(lines)


# Instance globale du service
metrics_service = MetricsService()
