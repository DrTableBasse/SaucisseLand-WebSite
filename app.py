from src.saucisseland import create_app
from src.saucisseland.routes import api  # Adjust the import path as needed

app = create_app()


app.register_blueprint(api)

if __name__ == "__main__":
    app.run(debug=True)
