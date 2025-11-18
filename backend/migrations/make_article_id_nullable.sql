-- Migration pour rendre article_id nullable dans article_images
-- Permet l'upload d'images avant la création de l'article

ALTER TABLE article_images 
ALTER COLUMN article_id DROP NOT NULL;

