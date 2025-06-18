from . import conn


def get_server_info():
    cursor = conn.cursor()
    cursor.execute("SELECT name, description FROM server LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    return result
