from flask import Blueprint, render_template
import random
from dotenv import load_dotenv
import os
import requests

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
