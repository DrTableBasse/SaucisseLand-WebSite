from waitress import serve
from wsgi import app
print("Server is running on http://127.0.0.1:8000")
serve(app, host="127.0.0.1", port=8000)

