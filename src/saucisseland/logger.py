import logging
import os

# Dossier pour les logs
log_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
os.makedirs(log_dir, exist_ok=True)

# Accès
access_logger = logging.getLogger("access")
access_logger.setLevel(logging.INFO)
access_handler = logging.FileHandler(os.path.join(log_dir, "access.log"))
access_handler.setFormatter(logging.Formatter(
    "[%(asctime)s][%(levelname)s] %(message)s"
))
access_logger.addHandler(access_handler)

# Erreurs
error_logger = logging.getLogger("error")
error_logger.setLevel(logging.ERROR)
error_handler = logging.FileHandler(os.path.join(log_dir, "error.log"))
error_handler.setFormatter(logging.Formatter(
    "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
))
error_logger.addHandler(error_handler)
