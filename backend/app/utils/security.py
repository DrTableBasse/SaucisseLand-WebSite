"""Utilitaires de sécurité pour sanitizer les inputs utilisateurs."""
import bleach
import markdown
from markdown.extensions import codehilite, fenced_code, tables

# Configuration de bleach pour autoriser uniquement les balises Markdown sécurisées
ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 's', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'blockquote', 'code', 'pre', 'a', 'img', 'hr',
    'table', 'thead', 'tbody', 'tr', 'th', 'td', 'del', 'ins', 'sub', 'sup'
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target', 'rel'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    'code': ['class'],
    'pre': ['class'],
    'table': ['class'],
    'th': ['align', 'colspan', 'rowspan'],
    'td': ['align', 'colspan', 'rowspan'],
}

ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']

ALLOWED_STYLES = []


def sanitize_html(html: str) -> str:
    """Sanitize le HTML pour éviter les attaques XSS.
    
    Args:
        html: HTML à sanitizer
    
    Returns:
        str: HTML sanitizé
    """
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        styles=ALLOWED_STYLES,
        strip=True
    )


def sanitize_markdown(markdown_text: str) -> str:
    """Convertit le Markdown en HTML et le sanitize.
    
    Args:
        markdown_text: Texte Markdown à convertir et sanitizer
    
    Returns:
        str: HTML sanitizé
    """
    # Convertir Markdown en HTML
    md = markdown.Markdown(
        extensions=[
            'codehilite',
            'fenced_code',
            'tables',
            'nl2br',
            'sane_lists'
        ],
        extension_configs={
            'codehilite': {
                'css_class': 'highlight'
            }
        }
    )
    html = md.convert(markdown_text)
    
    # Sanitizer le HTML généré
    return sanitize_html(html)


def sanitize_text(text: str, max_length: int = None) -> str:
    """Sanitize un texte simple (titre, slug, excerpt, etc.).
    
    Args:
        text: Texte à sanitizer
        max_length: Longueur maximale (optionnel)
    
    Returns:
        str: Texte sanitizé
    """
    if not text:
        return ""
    
    # Échapper les caractères HTML
    sanitized = bleach.clean(text, tags=[], strip=True)
    
    # Limiter la longueur si spécifié
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()


def sanitize_slug(slug: str) -> str:
    """Sanitize un slug pour qu'il soit URL-safe.
    
    Args:
        slug: Slug à sanitizer
    
    Returns:
        str: Slug sanitizé
    """
    import re
    
    if not slug:
        return ""
    
    # Nettoyer le slug
    sanitized = bleach.clean(slug, tags=[], strip=True)
    
    # Garder uniquement les caractères alphanumériques, tirets et underscores
    sanitized = re.sub(r'[^\w\-_]', '', sanitized)
    
    return sanitized.strip()

