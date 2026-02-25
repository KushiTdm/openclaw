#!/usr/bin/env python3
"""
migrate_db.py - Migration DB existante vers v3
Ajoute: website, has_website, transferred_to
Usage: python3 migrate_db.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path.home() / ".openclaw/workspace/prospecting.db"

def migrate():
    if not DB_PATH.exists():
        print(f"❌ DB non trouvée: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    migrations = [
        ("website", "ALTER TABLE prospects ADD COLUMN website TEXT"),
        ("has_website", "ALTER TABLE prospects ADD COLUMN has_website BOOLEAN DEFAULT FALSE"),
        ("transferred_to", "ALTER TABLE prospects ADD COLUMN transferred_to TEXT"),
        # Ajouter nouveaux statuts à la table method_stats
        ("audit_gratuit_method", "INSERT OR IGNORE INTO method_stats (method_name) VALUES ('audit_gratuit')"),
    ]

    for name, sql in migrations:
        try:
            cursor.execute(sql)
            print(f"✅ Migration '{name}' appliquée")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print(f"⏭️  Migration '{name}' déjà appliquée")
            else:
                print(f"❌ Migration '{name}' erreur: {e}")

    # Mettre à jour has_website pour les prospects existants qui ont un website
    cursor.execute("UPDATE prospects SET has_website=1 WHERE website IS NOT NULL AND website != ''")
    updated = cursor.rowcount
    if updated > 0:
        print(f"✅ {updated} prospects mis à jour avec has_website=True")

    conn.commit()
    conn.close()
    print("\n✅ Migration terminée!")

    # Vérifier la structure
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(prospects)")
    columns = [row[1] for row in cursor.fetchall()]
    conn.close()
    print(f"\n📋 Colonnes actuelles: {', '.join(columns)}")

if __name__ == "__main__":
    migrate()