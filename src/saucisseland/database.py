import sqlite3


def get_server_info():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, description FROM server LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    return result
