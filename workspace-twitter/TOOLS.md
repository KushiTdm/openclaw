# TOOLS.md - Outils Twitter X

## API Twitter/X

**Version :** API v2 (Basic Plan - $100/mois)
**Credentials :** `~/.openclaw/credentials/twitter.json`

### Limites Quotidiennes
- Tweets: 3,000/mois (~100/jour)
- Media uploads: Inclus dans quota
- Rate limit reset: Début du mois

### Formats Images
- JPG, PNG, GIF, WEBP
- Max 5 MB par image
- Max 4 images par tweet

## Scripts Disponibles

### twitter_poster.py

**Localisation :** `~/.openclaw/workspace-twitter/scripts/twitter_poster.py`

**Usage :**
```bash
# Single tweet
python3 ~/.openclaw/workspace-twitter/scripts/twitter_poster.py \
  --type single \
  --text "Mon tweet"

# Avec images
python3 ~/.openclaw/workspace-twitter/scripts/twitter_poster.py \
  --type single \
  --text "Texte" \
  --images img1.jpg img2.png

# Thread
python3 ~/.openclaw/workspace-twitter/scripts/twitter_poster.py \
  --type thread \
  --file thread.json
```

**Arguments :**
- `--type` : `single` ou `thread` (requis)
- `--text` : Texte du tweet (pour single)
- `--images` : Liste de chemins d'images (optionnel)
- `--file` : Fichier JSON de config (pour thread)

### thread_splitter.py

**Localisation :** `~/.openclaw/workspace-twitter/scripts/thread_splitter.py`

**Usage :**
```bash
python3 ~/.openclaw/workspace-twitter/scripts/thread_splitter.py \
  --input "Texte complet" \
  --output thread.json
```

**Arguments :**
- `--input` : Texte complet à découper (requis)
- `--output` : Fichier JSON de sortie (optionnel, affiche à l'écran si omis)
- `--no-indicators` : Ne pas ajouter les numéros 1/N (optionnel)

**Sortie JSON :**
```json
{
  "tweets": [
    {"text": "1/3 Premier tweet...", "images": []},
    {"text": "2/3 Deuxième tweet...", "images": []},
    {"text": "3/3 Troisième tweet...", "images": []}
  ]
}
```

## Logs

**Path :** `~/.openclaw/workspace-twitter/memory/YYYY-MM-DD.md`

**Contenu :**
- Timestamps publications
- URLs tweets
- Stats quotidiennes
- Erreurs éventuelles

## Credentials

**Fichier :** `~/.openclaw/credentials/twitter.json`

**Format :**
```json
{
  "api_key": "VOTRE_API_KEY",
  "api_secret": "VOTRE_API_SECRET",
  "access_token": "VOTRE_ACCESS_TOKEN",
  "access_token_secret": "VOTRE_ACCESS_TOKEN_SECRET"
}
```

**Permissions requises :**
- Read and Write (OAuth 1.0a)
- User Context
- Basic Plan souscrit ($100/mois)

## Workflow Complet

### Publication Tweet Simple

1. Anna envoie : "Poste un tweet : 'Hello'"
2. Tu exécutes :
```bash
python3 ~/.openclaw/workspace-twitter/scripts/twitter_poster.py \
  --type single \
  --text "Hello"
```
3. Script retourne URL
4. Tu logs dans `memory/YYYY-MM-DD.md`
5. Tu réponds à Anna avec l'URL

### Publication Thread

1. Anna envoie texte long
2. Tu découpes :
```bash
python3 ~/.openclaw/workspace-twitter/scripts/thread_splitter.py \
  --input "Texte long..." \
  --output /tmp/thread.json
```
3. Tu publies :
```bash
python3 ~/.openclaw/workspace-twitter/scripts/twitter_poster.py \
  --type thread \
  --file /tmp/thread.json
```
4. Tu logs les URLs
5. Tu réponds à Anna avec toutes les URLs

### Publication avec Images

1. Anna fournit image(s) dans `/mnt/user-data/uploads/`
2. Tu publies :
```bash
python3 ~/.openclaw/workspace-twitter/scripts/twitter_poster.py \
  --type single \
  --text "Texte" \
  --images "/mnt/user-data/uploads/image.jpg"
```
3. Tu logs
4. Tu réponds à Anna

## Commandes Utiles

### Vérifier quota restant
```bash
# Compter tweets du mois en cours
grep -c "Tweet publié" ~/.openclaw/workspace-twitter/memory/2026-02-*.md
```

### Compresser une image
```bash
convert /path/to/image.jpg -quality 85 /path/to/image_compressed.jpg
```

### Tester credentials
```bash
python3 ~/.openclaw/workspace-twitter/scripts/twitter_poster.py \
  --type single \
  --text "Test"
```

## Dépendances Python
```bash
pip install --break-system-packages tweepy Pillow
```

**Versions :**
- tweepy >= 4.14.0
- Pillow >= 10.0.0
