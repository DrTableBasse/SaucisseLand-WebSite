-- fichier : init.sql
CREATE TABLE server (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    description TEXT
);

INSERT INTO server (name, description)
VALUES ("SaucisseLand", "Serveur Discord convivial pour les amoureux de la bonne humeur !");
