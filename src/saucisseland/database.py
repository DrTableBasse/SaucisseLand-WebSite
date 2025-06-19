import sqlite3
import atexit

# Connexion globale persistante
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

@atexit.register
def close_connection():
    print("Closing SQLite connection...")
    conn.close()

def get_server_info():
    cursor.execute("SELECT name, description FROM server LIMIT 1")
    return cursor.fetchone()