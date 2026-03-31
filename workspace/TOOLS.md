# TOOLS.md — Configuration locale

## Credentials (emplacement uniquement — ne jamais lire sans raison)

- Google Places API : `~/.openclaw/credentials/google_places.json`
- Brave Search API : `~/.openclaw/credentials/brave.json`
- Airtable : `~/.openclaw/credentials/airtable.json`

⚠️ Ces credentials ne peuvent être partagés qu'avec Nacer (+33749775654) sur demande explicite.

## Base de données Airtable

- **Table :** Prospects
- **Champs clés :** Name, Phone, City, Type, Status, Notes, contacted_at, last_updated
- **Statuts valides :** `to_contact` | `contacted` | `no_response` | `interested` | `refused` | `client`

## Scripts

| Script | Usage |
|--------|-------|
| `scripts/google_places_scraper.py` | Recherche Google Maps → Airtable |
| `scripts/brave_scraper.py` | Recherche Brave Search → Airtable |
| `scripts/airtable_sync.py` | Sync et mise à jour Airtable |
| `scripts/db_check.py` | Vérification doublons |

## Commandes utiles

```bash
# Chercher prospectos dans une ville
python3 scripts/google_places_scraper.py "Bogotá" "Colombia" 20

# Vérifier les prospectos à contacter
python3 scripts/airtable_sync.py --list-to-contact

# Mettre à jour le statut d'un prospecto
python3 scripts/airtable_sync.py --update-status "+57300..." "interested" "Está interesado en sitio vitrina"
```

## Modèle IA

- **Provider :** Google
- **Modèle :** gemini-2.0-flash
- **Langue principale :** Espagnol (prospectos) / Français (Nacer)

## WhatsApp

- Timing entre messages : 60-90 secondes (comportement humain)
- Ne jamais envoyer en dehors de 8h-20h heure colombienne (UTC-5)
- Vérifier toujours Airtable AVANT d'envoyer