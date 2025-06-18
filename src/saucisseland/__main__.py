import atexit
import sqlite3
import sys
from . import app

# argparse
if 'init_db' in sys.argv:
    ...


conn = sqlite3.connect('database.db')
atexit.register(conn.close)

app.run(debug=True)
