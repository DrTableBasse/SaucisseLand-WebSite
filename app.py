from src.saucisseland import create_app
from src.saucisseland.routes import api  # Adjust the import path as needed
from flask import render_template
app = create_app()


app.register_blueprint(api)

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404

if __name__ == "__main__":
    app.run(debug=True)
