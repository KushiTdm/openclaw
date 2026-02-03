# TOOLS.md - Outils et Configuration

## Base de Données SQLite

**Path:** `~/.openclaw/workspace/prospecting.db`

**Schéma (à créer au premier lancement):**
```sql
CREATE TABLE IF NOT EXISTS prospects (
  phone_number TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  business_name TEXT,
  city TEXT,
  country TEXT,
  type TEXT CHECK(type IN ('hotel','hostel','lodge','tour_operator')),
  source TEXT DEFAULT 'google_places',
  google_maps_url TEXT,
  address TEXT,
  rating REAL,
  review_count INTEGER,
  status TEXT DEFAULT 'new' CHECK(status IN ('new','contacted','interested','not_interested','closed')),
  notes TEXT,
  contacted_at DATETIME,
  last_response_at DATETIME,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_status ON prospects(status);
CREATE INDEX idx_created_at ON prospects(created_at);
CREATE INDEX idx_city ON prospects(city);
```

**Commandes utiles:**
```bash
# Voir tous les prospects
sqlite3 ~/.openclaw/workspace/prospecting.db "SELECT * FROM prospects;"

# Compter par statut
sqlite3 ~/.openclaw/workspace/prospecting.db "SELECT status, COUNT(*) FROM prospects GROUP BY status;"

# Prospects à contacter aujourd'hui
sqlite3 ~/.openclaw/workspace/prospecting.db "SELECT phone_number, name FROM prospects WHERE status='new' LIMIT 10;"
```

## APIs Configurées

### Google Places API
- **Clé:** Stockée dans `~/.openclaw/credentials/google_places.json`
- **Quota gratuit:** 200$/mois (~40,000 requêtes)
- **Usage optimal:** Text Search (1 req/ville) + Place Details si nécessaire
- **Rate limit:** Max 20 requêtes/session pour économiser
- **Documentation:** https://developers.google.com/maps/documentation/places/web-service

### Brave Search API (Secondaire)
- **Clé:** Dans `~/.openclaw/credentials/brave.json`
- **Usage:** Recherche complémentaire si Google bloqué
- **Quota:** 2000 req/mois gratuit

## Scripts de Prospection

### Scraper Google Places
**Path:** `~/.openclaw/workspace/scripts/google_places_scraper.py`
**Fonction:** Recherche établissements sans website
**Exécution:** Automatique via cron 2x/jour (10h, 18h heure Lima)

### Gestionnaire DB
**Path:** `~/.openclaw/workspace/scripts/db_manager.py`
**Fonction:** INSERT, UPDATE, vérification doublons

### Sync WhatsApp
**Path:** `~/.openclaw/workspace/scripts/whatsapp_handler.py`
**Fonction:** Envoi messages, logging réponses

## Horaires de Fonctionnement

**Prospection active:** 09:00-18:00 (heure locale cible)
**Envoi messages:** 09:00-20:00 (éviter nuit)
**Heartbeat check:** Toutes les 2h pour nouveaux prospects

## Logs

**Path:** `~/.openclaw/workspace/memory/prospecting_YYYY-MM-DD.md`

**Contenu quotidien:**
- Nombre de prospects trouvés
- Nombre contactés
- Taux de réponse
- Erreurs API
- Notes importantes

## Whitelist WhatsApp

**Path:** `~/.openclaw/config/whitelist.json`

**Structure:**
```json
{
  "admins": ["+33749775654"],
  "prospects": [],
  "auto_discovered": []
}
```

Ajouter automatiquement les nouveaux prospects qualifiés dans `auto_discovered`.
