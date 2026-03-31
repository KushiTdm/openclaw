#!/usr/bin/env python3
"""
Airtable Sync — Anna / NeuraWeb
Gère la mise à jour des statuts prospects dans Airtable.

Usage:
  python3 airtable_sync.py --list-to-contact
  python3 airtable_sync.py --list-all
  python3 airtable_sync.py --update-status "+57300..." "interested" "Notes ici"
  python3 airtable_sync.py --stats
  python3 airtable_sync.py --check-duplicate "+57300..."
"""

import json
import sys
from datetime import datetime
from pathlib import Path

AIRTABLE_CREDENTIALS = Path.home() / ".openclaw/credentials/airtable.json"

VALID_STATUSES = ["to_contact", "contacted", "no_response", "interested", "refused", "client"]


def load_table():
    if not AIRTABLE_CREDENTIALS.exists():
        print("❌ Credentials Airtable non trouvés:", AIRTABLE_CREDENTIALS)
        return None
    with open(AIRTABLE_CREDENTIALS) as f:
        creds = json.load(f)
    try:
        from pyairtable import Api
        api = Api(creds["api_key"])
        table = api.table(creds["base_id"], "Prospects")
        print("✅ Connecté à Airtable")
        return table
    except Exception as e:
        print(f"❌ Erreur connexion: {e}")
        return None


def list_to_contact(table, city=None):
    """Liste les prospects à contacter."""
    formula = "Status = 'to_contact'"
    if city:
        formula = f"AND(Status = 'to_contact', City = '{city}')"
    try:
        records = table.all(formula=formula)
        print(f"\n📋 Prospects à contacter{' à ' + city if city else ''}: {len(records)}\n")
        for r in records:
            f = r["fields"]
            print(f"  📱 {f.get('Name', '?')} | {f.get('Phone', '?')} | {f.get('City', '?')} | {f.get('Type', '?')}")
        return records
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return []


def list_all(table):
    """Affiche les stats par statut."""
    try:
        records = table.all()
        by_status = {}
        for r in records:
            status = r["fields"].get("Status", "unknown")
            by_status[status] = by_status.get(status, 0) + 1

        print(f"\n📊 Total prospects: {len(records)}")
        for status, count in sorted(by_status.items()):
            print(f"   {status}: {count}")
        return records
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return []


def update_status(table, phone, new_status, notes=None):
    """Met à jour le statut d'un prospect par son numéro de téléphone."""
    if new_status not in VALID_STATUSES:
        print(f"❌ Statut invalide: {new_status}")
        print(f"   Valides: {', '.join(VALID_STATUSES)}")
        return False

    phone_clean = phone.replace(" ", "")
    try:
        records = table.all(formula=f"Phone = '{phone_clean}'")
        if not records:
            print(f"❌ Prospect non trouvé: {phone_clean}")
            return False

        record_id = records[0]["id"]
        fields = {"Status": new_status, "last_updated": datetime.now().isoformat()}

        if new_status == "contacted" and not records[0]["fields"].get("contacted_at"):
            fields["contacted_at"] = datetime.now().isoformat()

        if notes:
            existing_notes = records[0]["fields"].get("Notes", "")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            new_note = f"[{timestamp}] {notes}"
            fields["Notes"] = f"{existing_notes}\n{new_note}".strip() if existing_notes else new_note

        table.update(record_id, fields)
        print(f"✅ Mis à jour: {records[0]['fields'].get('Name', phone_clean)} → {new_status}")
        return True

    except Exception as e:
        print(f"❌ Erreur mise à jour: {e}")
        return False


def check_duplicate(table, phone):
    """Vérifie si un numéro est déjà dans Airtable."""
    phone_clean = phone.replace(" ", "")
    try:
        records = table.all(formula=f"Phone = '{phone_clean}'")
        if records:
            r = records[0]["fields"]
            print(f"⚠️ DOUBLON: {r.get('Name', '?')} ({phone_clean}) — Status: {r.get('Status', '?')}")
            return True
        else:
            print(f"✅ Pas de doublon pour {phone_clean}")
            return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def get_stats(table):
    """Retourne les stats complètes."""
    try:
        records = table.all()
        today = datetime.now().strftime("%Y-%m-%d")
        by_status = {}
        by_city = {}
        contacted_today = 0

        for r in records:
            f = r["fields"]
            status = f.get("Status", "unknown")
            city = f.get("City", "unknown")
            contacted_at = f.get("contacted_at", "")

            by_status[status] = by_status.get(status, 0) + 1
            by_city[city] = by_city.get(city, 0) + 1

            if contacted_at and contacted_at.startswith(today):
                contacted_today += 1

        print(f"\n{'='*50}")
        print(f"📊 STATS AIRTABLE — {today}")
        print(f"{'='*50}")
        print(f"Total: {len(records)}")
        print(f"Contactés aujourd'hui: {contacted_today}")
        print(f"\nPar statut:")
        for s, c in sorted(by_status.items()):
            print(f"  {s}: {c}")
        print(f"\nPar ville (top 5):")
        for city, count in sorted(by_city.items(), key=lambda x: -x[1])[:5]:
            print(f"  {city}: {count}")
        print(f"{'='*50}\n")

    except Exception as e:
        print(f"❌ Erreur stats: {e}")


if __name__ == "__main__":
    table = load_table()
    if not table:
        sys.exit(1)

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "--list-to-contact":
        city = sys.argv[2] if len(sys.argv) >= 3 else None
        list_to_contact(table, city)

    elif cmd == "--list-all":
        list_all(table)

    elif cmd == "--update-status":
        if len(sys.argv) < 4:
            print("Usage: --update-status <phone> <status> [notes]")
            sys.exit(1)
        phone = sys.argv[2]
        status = sys.argv[3]
        notes = sys.argv[4] if len(sys.argv) >= 5 else None
        update_status(table, phone, status, notes)

    elif cmd == "--check-duplicate":
        if len(sys.argv) < 3:
            print("Usage: --check-duplicate <phone>")
            sys.exit(1)
        check_duplicate(table, sys.argv[2])

    elif cmd == "--stats":
        get_stats(table)

    else:
        print(f"❌ Commande inconnue: {cmd}")
        print(__doc__)