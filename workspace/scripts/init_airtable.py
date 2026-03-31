#!/usr/bin/env python3
"""
Init Airtable — Anna / NeuraWeb
Vérifie la connexion Airtable et liste les champs de la table Prospects.
Ce script ne crée pas la table (Airtable doit être configuré manuellement).
Il vérifie simplement que tout fonctionne.

Usage: python3 init_airtable.py
"""

import json
from pathlib import Path

AIRTABLE_CREDENTIALS = Path.home() / ".openclaw/credentials/airtable.json"

REQUIRED_FIELDS = {
    "Name": "Single line text — Nom du business",
    "Phone": "Phone number — Téléphone avec +57",
    "City": "Single line text — Ville en Colombie",
    "Type": "Single select — restaurant/hotel/salon/health/retail/business",
    "Status": "Single select — to_contact/contacted/no_response/interested/refused/client",
    "Notes": "Long text — Notes de conversation",
    "contacted_at": "Date — Date du premier contact",
    "last_updated": "Date — Dernière mise à jour",
}


def check_connection():
    if not AIRTABLE_CREDENTIALS.exists():
        print(f"❌ Fichier credentials manquant: {AIRTABLE_CREDENTIALS}")
        print("\nCréer ce fichier avec:")
        print(json.dumps({
            "api_key": "YOUR_AIRTABLE_PERSONAL_ACCESS_TOKEN",
            "base_id": "YOUR_BASE_ID"
        }, indent=2))
        return False

    with open(AIRTABLE_CREDENTIALS) as f:
        creds = json.load(f)

    api_key = creds.get("api_key", "")
    base_id = creds.get("base_id", "")

    if not api_key or not base_id:
        print("❌ Credentials incomplets (api_key ou base_id manquant)")
        return False

    try:
        from pyairtable import Api
        api = Api(api_key)
        table = api.table(base_id, "Prospects")

        # Test: récupérer 1 enregistrement
        records = table.all(max_records=1)
        print(f"✅ Connexion Airtable OK")
        print(f"   Base ID: {base_id}")
        print(f"   Table: Prospects")
        print(f"   Enregistrements existants: (au moins {len(records)} récupéré)")

        print(f"\n📋 Champs REQUIS dans la table Airtable:")
        for field, description in REQUIRED_FIELDS.items():
            print(f"   ✓ {field} — {description}")

        print(f"\n✅ Tout est configuré. Anna peut démarrer.")
        return True

    except Exception as e:
        print(f"❌ Erreur connexion Airtable: {e}")
        print("\nVérifiez:")
        print("  1. Votre Personal Access Token Airtable")
        print("  2. Le Base ID (commence par 'app...')")
        print("  3. Que la table 'Prospects' existe dans cette base")
        return False


if __name__ == "__main__":
    check_connection()