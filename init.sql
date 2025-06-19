-- fichier : init.sql
CREATE TABLE  IF NOT EXISTS server (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    description TEXT
);

INSERT INTO server (name, description)
VALUES ("SaucisseLand", "Serveur Discord convivial pour les amoureux de la bonne humeur !");

CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    content_html TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);