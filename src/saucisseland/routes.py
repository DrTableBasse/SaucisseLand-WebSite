
from flask import Blueprint, render_template
import random
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
    #return "<h2>Mentions légales</h2><p>Site créé à des fins personnelles.</p>"
    return render_template("legal.html")
@main.route("/contact")
def contact():
    return "<h2>Contact</h2><p>Contactez-nous via Discord : SaucisseLand#1234</p>"
