# Migrations de base de données

## Migration 1: Rendre article_id nullable

Cette migration permet d'uploader des images avant la création d'un article.

### Exécution de la migration

#### Option 1: Via Python (depuis le conteneur Docker)

```bash
docker exec discord_blog_backend python migrations/make_article_id_nullable.py
```

#### Option 2: Via SQL direct (depuis le conteneur PostgreSQL)

```bash
docker exec -i discord_blog_db psql -U user -d discord_blog < migrations/make_article_id_nullable.sql
```

#### Option 3: Via psql interactif

```bash
docker exec -it discord_blog_db psql -U user -d discord_blog
```

Puis exécutez:
```sql
ALTER TABLE article_images ALTER COLUMN article_id DROP NOT NULL;
```

### Vérification

Pour vérifier que la migration a réussi:

```sql
SELECT is_nullable 
FROM information_schema.columns 
WHERE table_name = 'article_images' 
AND column_name = 'article_id';
```

Le résultat devrait être `YES`.

---

## Migration 2: Créer la table article_likes

Cette migration crée la table `article_likes` pour gérer les likes uniques par utilisateur.

### Exécution de la migration

#### Option 1: Via Python (depuis le conteneur Docker)

```bash
docker exec discord_blog_backend python migrations/add_article_likes_table.py
```

#### Option 2: Via SQL direct (depuis le conteneur PostgreSQL)

```bash
docker exec -i discord_blog_db psql -U user -d discord_blog < migrations/add_article_likes_table.sql
```

#### Option 3: Via psql interactif

```bash
docker exec -it discord_blog_db psql -U user -d discord_blog
```

Puis exécutez le contenu de `migrations/add_article_likes_table.sql`.

### Vérification

Pour vérifier que la migration a réussi:

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_name = 'article_likes';
```

Le résultat devrait retourner `article_likes`.

