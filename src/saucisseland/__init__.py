import importlib.resources

from flask import Flask, render_template

from . import routes


app = Flask(
    __name__,
    # move both folders unders src/saucisseland
    # PIP INSTALL -E . SINON SAMARCHPA
    template_folder=importlib.resources.path('saucisseland', "templates"),
    static_folder=importlib.resources.path('saucisseland', "static"),
)

app.register_blueprint(routes.main)
app.register_blueprint(routes.api)


@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404
