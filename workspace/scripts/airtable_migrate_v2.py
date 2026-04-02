#!/usr/bin/env python3
"""
airtable_migrate_v2.py — Migration Airtable vers la v2 (prospection mondiale)
Ajoute les champs manquants dans la table Prospects pour le tracking global.

IMPORTANT : Airtable ne permet PAS d'ajouter des colonnes via l'API.
Ce script :
  1. Liste les champs actuels pour diagnostic
  2. Génère la liste des champs à créer manuellement dans Airtable
  3. Vérifie que les champs requis sont bien présents

Créer les champs manuellement dans Airtable UI, puis relancer ce script
pour vérification.

Usage: python3 airtable_migrate_v2.py
"""

import json
from pathlib import Path

AIRTABLE_CREDS = Path.home() / ".openclaw/credentials/airtable.json"

# Champs requis pour la v2 (nom Airtable → type → description)
REQUIRED_FIELDS_V2 = {
    # Champs existants (ne pas recréer)
    "Name":               ("Single line text",  "Nom de l'établissement"),
    "Phone":              ("Phone number",       "Numéro avec code pays (+XX...)"),
    "City":               ("Single line text",   "Ville"),
    "Type":               ("Single select",      "restaurant/hotel/salon/health/retail/business/Individual/Corporate"),
    "Status":             ("Single select",      "to_contact/contacted/no_response/interested/qualified/refused/client"),
    "Notes":              ("Long text",          "Résumé de la conversation"),
    "contacted_at":       ("Date",               "Date du premier contact"),
    "last_updated":       ("Date",               "Dernière mise à jour"),
    "Lead Score (AI)":    ("Number",             "Score IA (généré automatiquement)"),
    "Contact Summary (AI)": ("Long text",        "Résumé IA de la conversation"),

    # NOUVEAUX champs v2 (à créer dans Airtable UI)
    "Country":            ("Single line text",   "Code pays ISO (CO, MX, BR, IN, NG...)"),
    "Language":           ("Single line text",   "Langue utilisée (es, en, fr, pt, ar, de...)"),
    "Template_used":      ("Single line text",   "ID template (A, B, C, D)"),
    "Message_type":       ("Single select",      "text / voice"),
    "Response_type":      ("Single select",      "positive / negative / objection / silence"),
    "Objection":          ("Single line text",   "no_budget / has_instagram / has_website / not_interested / timing / other"),
    "Price_discussed":    ("Checkbox",           "Cocher si le prospect a demandé un prix"),
    "Price_quoted":       ("Number",             "Montant proposé (en devise locale)"),
    "Market_price_ref":   ("Number",             "Prix médian marché local trouvé via Gemini"),
}

EXISTING_FIELDS = {
    "Name", "Phone", "City", "Type", "Status", "Notes",
    "contacted_at", "last_updated", "Lead Score (AI)", "Contact Summary (AI)"
}

NEW_FIELDS = {k: v for k, v in REQUIRED_FIELDS_V2.items() if k not in EXISTING_FIELDS}


def check_connection():
    if not AIRTABLE_CREDS.exists():
        print(f"❌ Credentials Airtable manquants : {AIRTABLE_CREDS}")
        return None
    with open(AIRTABLE_CREDS) as f:
        creds = json.load(f)
    try:
        from pyairtable import Api
        api = Api(creds["api_key"])
        table = api.table(creds["base_id"], "Prospects")
        # Test de connexion
        records = table.all(max_records=1)
        print(f"✅ Connexion Airtable OK — {len(records)} record(s) de test")
        return table
    except Exception as e:
        print(f"❌ Erreur connexion : {e}")
        return None


def detect_existing_columns(table):
    """Détecte les colonnes présentes dans Airtable via les champs du premier record."""
    records = table.all(max_records=5)
    detected = set()
    for r in records:
        detected.update(r.get("fields", {}).keys())
    return detected


def print_migration_guide():
    """Affiche le guide de migration pour Airtable."""
    print("\n" + "=" * 62)
    print("📋 CHAMPS À CRÉER MANUELLEMENT DANS AIRTABLE UI")
    print("=" * 62)
    print("\nProcédure :")
    print("  1. Ouvrir Airtable → Base NeuraWeb → Table 'Prospects'")
    print("  2. Cliquer sur '+' à droite des colonnes existantes")
    print("  3. Créer chaque champ ci-dessous\n")

    for name, (field_type, description) in NEW_FIELDS.items():
        print(f"  ┌─ Nom du champ : {name}")
        print(f"  │  Type         : {field_type}")
        print(f"  │  Description  : {description}")

        if field_type == "Single select":
            options = description.replace(" ", "").split("/")
            print(f"  │  Options      : {', '.join(options)}")
        print(f"  └{'─' * 48}")

    print("\n⚠️  Les options 'Single select' doivent être créées exactement comme indiqué.")
    print("   Relancer ce script après création pour vérification.\n")


def verify_fields(table):
    """Vérifie que tous les champs requis sont présents."""
    detected = detect_existing_columns(table)

    print("\n📊 VÉRIFICATION DES CHAMPS :")
    print("-" * 62)

    missing = []
    for name in REQUIRED_FIELDS_V2:
        if name in detected:
            print(f"  ✅ {name}")
        else:
            print(f"  ❌ {name}  ← À créer")
            missing.append(name)

    print(f"\n{'=' * 62}")
    if not missing:
        print("🎉 Tous les champs sont présents. Migration complète !")
        return True
    else:
        print(f"⚠️  {len(missing)} champ(s) manquant(s) :")
        for m in missing:
            ft, desc = REQUIRED_FIELDS_V2[m]
            print(f"   - {m} ({ft})")
        print("\n→ Créer ces champs dans Airtable UI puis relancer ce script.")
        return False


def test_write_new_fields(table, detected_fields):
    """Teste l'écriture dans les nouveaux champs sur un record existant."""
    new_present = [f for f in NEW_FIELDS if f in detected_fields]
    if not new_present:
        print("\n⚠️  Aucun nouveau champ disponible pour le test d'écriture.")
        return

    records = table.all(max_records=1, formula="Status = 'to_contact'")
    if not records:
        print("\n⚠️  Aucun record 'to_contact' pour tester l'écriture.")
        return

    record_id = records[0]["id"]
    test_data = {}
    if "Country" in new_present:
        test_data["Country"] = "TEST"
    if "Language" in new_present:
        test_data["Language"] = "test"

    if not test_data:
        return

    try:
        # Test write
        table.update(record_id, test_data)
        # Cleanup
        cleanup = {k: None for k in test_data}
        table.update(record_id, {k: "" for k in test_data if k == "Country" or k == "Language"})
        print(f"\n✅ Test d'écriture réussi sur les nouveaux champs.")
    except Exception as e:
        print(f"\n❌ Erreur d'écriture : {e}")


if __name__ == "__main__":
    print("\n🔧 Migration Airtable v2 — Prospection Mondiale Anna")
    print("=" * 62)

    table = check_connection()
    if not table:
        exit(1)

    # 1. Guide de migration
    print_migration_guide()

    # 2. Vérification de l'état actuel
    complete = verify_fields(table)

    if complete:
        # 3. Test d'écriture (si tout est en place)
        detected = detect_existing_columns(table)
        test_write_new_fields(table, detected)
        print("\n✅ Airtable prêt pour la prospection mondiale !")
    else:
        print("\n→ Complétez la migration dans Airtable UI et relancez.")