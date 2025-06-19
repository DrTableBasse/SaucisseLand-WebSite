import os
from flask import Flask, request
from .logger import access_logger, error_logger

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

    from .routes import main

    app.register_blueprint(main)

    # Log avant requête (IP, méthode, chemin, user-agent)
    @app.before_request
    def log_request_info():
        ip = request.remote_addr or "unknown"
        method = request.method
        path = request.path
        user_agent = request.headers.get("User-Agent", "unknown")
        # on va logger le status dans after_request à la place, donc ici on n'ajoute pas le status

    # Log après requête (statut réponse)
    @app.after_request
    def log_response_info(response):
        ip = request.remote_addr or "unknown"
        method = request.method
        path = request.path
        status = response.status_code
        user_agent = request.headers.get("User-Agent", "unknown")
        access_logger.info(f"{ip} - {method} {path} [Status {status}] - {user_agent}")
        return response

    # Gestion globale des erreurs inattendues
    @app.errorhandler(Exception)
    def handle_exception(e):
        error_logger.exception("Unhandled Exception:")
        return "Internal Server Error", 500

    return app
