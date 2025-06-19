"""
Module de gestion des routes principales et API pour le site SaucisseLand.
Ce fichier définit les pages publiques, l'ajout d'articles, et l'intégration d'un webhook Discord.
"""

import os
import random
import sqlite3
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for
from dotenv import load_dotenv
import requests
import markdown

load_dotenv()

api = Blueprint("api", __name__)
main = Blueprint("main", __name__)

messages = [
    "Le serveur Discord des amateurs de charcuterie numérique.",
    "Le QG des passionnés de saucissons et pixels.",
    "Le repaire des geeks qui aiment la bonne bouffe.",
    "Rejoignez la saucisse révolution numérique !",
    "La communauté où le fun et la charcuterie se rencontrent.",
]


@main.route("/")
def index():
    """Affiche la page d'accueil avec un message aléatoire."""
    message = random.choice(messages)
    return render_template("index.html", message=message)


@main.route("/article")
def actualites():
    """Affiche la page des actualités."""
    return render_template("article.html")


@main.route("/legal")
def legal():
    """Affiche la page des mentions légales."""
    return render_template("mentions_legales.html")


@main.route("/contact")
def contact():
    """Affiche la page de contact."""
    return render_template("contact.html")


# @api.route("/test-blague")
# def test_blague():
#     """Appelle l'API Blagues et affiche une blague aléatoire."""
#     token = os.getenv("BLAGUES_API_TOKEN")
#     headers = {"Authorization": f"Bearer {token}"}
#     try:
#         response = requests.get("https://www.blagues-api.fr/api/random", headers=headers, timeout=5)
#         response.raise_for_status()
#         data = response.json()
#         blague = data.get("joke") or data.get("title") or "Blague non disponible"
#         reponse = data.get("answer") or data.get("content") or ""
#         return render_template("blague.html", blague=blague, reponse=reponse)
#     except requests.RequestException as e:
#         return f"Erreur lors de la récupération de la blague : {e}"


def get_db_connection():
    """Crée et retourne une connexion à la base de données SQLite."""
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


@main.route("/nouvel-article", methods=["GET", "POST"])
def nouvel_article():
    """Affiche un formulaire de création d'article et enregistre un nouvel article"""
    if request.method == "POST":
        titre = request.form["title"]
        contenu_markdown = request.form["content"]
        
        # Convertir le Markdown en HTML
        contenu_html = markdown.markdown(contenu_markdown)

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO articles (title, content, content_html, created_at) VALUES (?, ?, ?, ?)",
            (titre, contenu_markdown, contenu_html, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        article_id = cur.lastrowid
        conn.commit()
        conn.close()

        # Envoi du webhook Discord
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        base_url = os.getenv("BASE_URL", "http://localhost:5000")
        if webhook_url:
            article_url = f"{base_url}/articles/{article_id}"
            message = {
                "content": (
                    "📝 Un nouvel article a été publié sur SaucisseLand !\n"
                    f"👉 {article_url}"
                )
            }
            try:
                requests.post(webhook_url, json=message, timeout=5)
            except requests.RequestException as e:
                print("Erreur Webhook Discord:", e)

        return redirect(url_for("main.afficher_article", article_id=article_id))

    return render_template("nouvel_article.html", article=None)


@main.route("/articles/<int:article_id>")
def afficher_article(article_id):
    """Affiche un article spécifique par son ID."""
    conn = get_db_connection()
    article = conn.execute(
        "SELECT * FROM articles WHERE id = ?", (article_id,)
    ).fetchone()
    conn.close()

    if article is None:
        return render_template("404.html"), 404

    # Utiliser l'HTML stocké s'il existe, sinon convertir le Markdown
    if article["content_html"]:
        content_html = article["content_html"]
    else:
        # Fallback pour les anciens articles
        content_html = markdown.markdown(article["content"])
    
    return render_template("article.html", article=article, content_html=content_html)


# Gestion d'erreurs personnalisée
@main.app_errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


