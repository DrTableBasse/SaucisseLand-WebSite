from flask import Blueprint, render_template, request, redirect, url_for
import random
from dotenv import load_dotenv
import os
import requests
import sqlite3

load_dotenv()
api = Blueprint('api', __name__)
main = Blueprint('main', __name__)

messages = [
    "Le serveur Discord des amateurs de charcuterie numérique.",
    "Le QG des passionnés de saucissons et pixels.",
    "Le repaire des geeks qui aiment la bonne bouffe.",
    "Rejoignez la saucisse révolution numérique !",
    "La communauté où le fun et la charcuterie se rencontrent."
]

@main.route("/")
def index():
    message = random.choice(messages)
    return render_template("index.html", message=message)


@main.route("/actualites")
def actualites():
    return render_template("actualites.html")


@main.route("/legal")
def legal():
    return render_template("mentions_legales.html")

@main.route("/contact")
def contact():
    return render_template("contact.html")

@api.route("/test-blague")
def test_blague():
    token = os.getenv("BLAGUES_API_TOKEN")
    headers = {
        "Authorization": f"Bearer {token}"
    }
    try:
        response = requests.get("https://www.blagues-api.fr/api/random", headers=headers)
        response.raise_for_status()
        data = response.json()
        blague = data.get("joke") or data.get("title") or "Blague non disponible"
        reponse = data.get("answer") or data.get("content") or ""

        return render_template("blague.html", blague=blague, reponse=reponse)
    except Exception as e:
        return f"Erreur lors de la récupération de la blague : {e}"



def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


@main.route("/nouvel-article", methods=["GET", "POST"])
def nouvel_article():
    if request.method == "POST":
        titre = request.form["title"]
        contenu = request.form["content"]

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO articles (title, content) VALUES (?, ?)", (titre, contenu))
        article_id = cur.lastrowid
        conn.commit()
        conn.close()

        # Envoi du webhook Discord
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        base_url = os.getenv("BASE_URL", "http://localhost:5000")
        if webhook_url:
            article_url = f"{base_url}/articles/{article_id}"
            message = {
                "content": f"📝 Un nouvel article a été publié sur SaucisseLand !\n👉 {article_url}"
            }
            try:
                requests.post(webhook_url, json=message)
            except Exception as e:
                print("Erreur Webhook Discord:", e)

        return redirect(url_for("main.afficher_article", article_id=article_id))

    return render_template("nouvel_article.html")



@main.route("/articles/<int:article_id>")
def afficher_article(article_id):
    conn = get_db_connection()
    article = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
    conn.close()

    if article is None:
        return "Article non trouvé", 404

    return render_template("article.html", article=article)