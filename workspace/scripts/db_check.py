#!/usr/bin/env python3
"""
DB Check — Anna / NeuraWeb
Vérifie si un prospect existe déjà dans Airtable avant de l'ajouter.

Usage: python3 db_check.py "+57300..."
"""

import json
import sys
from pathlib import Path

AIRTABLE_CREDENTIALS = Path.home() / ".openclaw/credentials/airtable.json"


def check(phone):
    if not AIRTABLE_CREDENTIALS.exists():
        print("❌ Credentials Airtable non trouvés")
        return None
    with open(AIRTABLE_CREDENTIALS) as f:
        creds = json.load(f)
    try:
        from pyairtable import Api
        api = Api(creds["api_key"])
        table = api.table(creds["base_id"], "Prospects")
        phone_clean = phone.replace(" ", "")
        records = table.all(formula=f"Phone = '{phone_clean}'")
        if records:
            r = records[0]["fields"]
            print(f"⚠️ EXISTE: {r.get('Name', '?')} | Status: {r.get('Status', '?')} | Ville: {r.get('City', '?')}")
            return True
        else:
            print(f"✅ Nouveau prospect — peut être ajouté")
            return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 db_check.py <phone>")
        sys.exit(1)
    result = check(sys.argv[1])
    sys.exit(0 if result is False else 1)