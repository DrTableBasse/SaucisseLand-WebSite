import os
from flask import Flask, request, send_from_directory, render_template
from .logger import access_logger, error_logger
from datetime import datetime, timedelta

def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "templates")
        ),
        static_folder=os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "static")
        ),
    )

    # Configuration de production
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(days=365)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

    from .routes import main

    app.register_blueprint(main)

    # Log avant chaque requête
    @app.before_request
    def log_request():
        access_logger.info(
            f"{request.remote_addr} - {request.method} {request.path} - "
            f"{request.headers.get('User-Agent', 'Unknown')}"
        )

    # Headers de sécurité et cache pour les fichiers statiques
    @app.after_request
    def add_security_headers(response):
        # Headers de sécurité
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Cache pour les fichiers statiques
        if request.path.startswith('/static/'):
            if request.path.endswith(('.css', '.js')):
                response.headers['Cache-Control'] = 'public, max-age=31536000'  # 1 an
            elif request.path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg')):
                response.headers['Cache-Control'] = 'public, max-age=31536000'  # 1 an
            else:
                response.headers['Cache-Control'] = 'public, max-age=86400'  # 1 jour
        
        return response

    # Gestion d'erreurs
    @app.errorhandler(404)
    def not_found(error):
        error_logger.warning(f"Page non trouvée: {request.path}")
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        error_logger.error(f"Erreur serveur: {error}")
        return "Erreur interne du serveur", 500

    return app
