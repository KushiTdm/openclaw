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
  status TEXT DEFAULT 'new' CHECK(status IN ('new','to_contact','contacted','interested','not_interested','closed')),
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

**Initialiser la DB:**
```bash
sqlite3 ~/.openclaw/workspace/prospecting.db < ~/.openclaw/workspace/scripts/init_db.sql
```

**Commandes utiles:**
```bash
# Voir tous les prospects
sqlite3 ~/.openclaw/workspace/prospecting.db "SELECT * FROM prospects;"

# Compter par statut
sqlite3 ~/.openclaw/workspace/prospecting.db "SELECT status, COUNT(*) FROM prospects GROUP BY status;"

# Prospects à contacter aujourd'hui
sqlite3 ~/.openclaw/workspace/prospecting.db "SELECT phone_number, name, city FROM prospects WHERE status='to_contact' LIMIT 10;"

# Vérifier doublons avant INSERT
sqlite3 ~/.openclaw/workspace/prospecting.db "SELECT COUNT(*) FROM prospects WHERE phone_number='+51XXXXXXXXX';"
```

## APIs Configurées

### Google Places API
- **Clé:** Stockée dans `~/.openclaw/credentials/google_places.json`
- **Quota gratuit:** 200$/mois (~40,000 requêtes)
- **Usage optimal:** 
  - Text Search: 1 requête/ville (32$/1000 req)
  - Place Details: Seulement si pas de website dans résultat initial (17$/1000 req)
- **Rate limit:** Max 20 requêtes/session pour rester dans le gratuit
- **Documentation:** https://developers.google.com/maps/documentation/places/web-service

**Exemple de requête optimisée:**
```python
# 1 Text Search par ville (économique)
results = gmaps.places(query="hotel hostel {city_name}", language='es')

# Place Details UNIQUEMENT si website absent
for place in results['results']:
    if 'website' not in place:
        details = gmaps.place(place['place_id'], fields=['formatted_phone_number','website'])
```

### Brave Search API (Secondaire)
- **Clé:** Dans `~/.openclaw/credentials/brave.json`
- **Usage:** Recherche complémentaire si Google bloqué
- **Quota:** 2000 req/mois gratuit

### Airtable
- **Clé:** Dans `~/.openclaw/credentials/airtable.json`
- **Usage:** Synchronisation prospects pour Sandra
- **Base ID:** Stocké dans credentials
- **Table:** `Prospects` avec champs: Name, Phone, City, Status, Notes

## Scripts à Créer

### 1. init_db.sql
**Path:** `~/.openclaw/workspace/scripts/init_db.sql`
**Fonction:** Création du schéma de base de données

### 2. google_places_scraper.py
**Path:** `~/.openclaw/workspace/scripts/google_places_scraper.py`
**Fonction:** Recherche établissements sans website via Google Places API
**Exécution:** Manuel ou via cron 2x/jour (10h, 18h heure Lima)
**Dépendances:** `pip install googlemaps`

### 3. db_manager.py
**Path:** `~/.openclaw/workspace/scripts/db_manager.py`
**Fonction:** 
- INSERT nouveaux prospects (avec vérification doublons)
- UPDATE status
- SELECT pour récupération prospects to_contact
**Classes:** DatabaseManager avec méthodes insert_prospect(), update_status(), check_duplicate()

### 4. airtable_sync.py
**Path:** `~/.openclaw/workspace/scripts/airtable_sync.py`
**Fonction:**
- Récupérer prospects marqués "to_contact" dans Airtable
- Vérifier doublons dans prospecting.db
- Synchroniser statuts bi-directionnellement
**Dépendances:** `pip install pyairtable`

## Contacts Clés

**Sandra (Relais Commercial):** +33770277697
- Recevoir prospects qualifiés (status='interested')
- Format message: "Nouveau prospect: [Nom], [Ville], [Téléphone], Contexte: [notes]"

**Nacer (Admin):** Numéro principal
- Escalade technique
- Validation prix/délais

## Horaires de Fonctionnement

**Prospection active:** 09:00-18:00 (heure locale cible)
**Envoi messages WhatsApp:** 09:00-20:00 (éviter nuit)
**Heartbeat check:** Toutes les 2h pour:
  - Nouveaux prospects en DB
  - Sync Airtable
  - Réponses WhatsApp reçues

## Logs

**Path:** `~/.openclaw/workspace/memory/prospecting_YYYY-MM-DD.md`

**Contenu quotidien:**
- Nombre de prospects trouvés (par ville)
- Nombre contactés
- Taux de réponse
- Erreurs API (avec détails)
- Prospects transférés à Sandra
- Notes importantes

**Format log:**
```markdown
## 2026-01-31

### Prospection
- Ville: Sucre, Bolivie
- Prospects trouvés: 15
- Sans website: 7
- Ajoutés en DB: 5 (2 doublons)

### Contact
- Messages envoyés: 8
- Réponses: 3
- Intéressés: 1 (transféré Sandra)

### API Usage
- Google Places: 12 requêtes (60$/200$ gratuit ce mois)
- Erreurs: Aucune
```

## Workflow Complet

### Matin (09:00)
1. Lire `airtable_sync.py` pour récupérer prospects to_contact
2. Vérifier doublons via `db_manager.py`
3. Lancer `google_places_scraper.py` sur ville du jour
4. Préparer liste prospects à contacter

### Journée
1. Envoyer messages WhatsApp (délai 60-90s entre chaque)
2. Logger réponses dans DB
3. Transférer prospects intéressés à Sandra

### Soir (18:00)
1. Sync final Airtable
2. Générer stats journalières
3. Mettre à jour `memory/YYYY-MM-DD.md`

## Dépendances Python
```bash
pip install --break-system-packages googlemaps pyairtable sqlite3
```

## Sécurité

- Credentials stockés dans `~/.openclaw/credentials/*.json` (chmod 600)
- Jamais commit les clés API dans git
- Vérifier doublons AVANT tout INSERT
- Logger toutes les actions en DB
