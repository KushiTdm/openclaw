#!/usr/bin/env python3
"""
Database Manager v3 - Anna Prospection
Nouveautés: has_website, website, transferred_to, stats améliorées
"""

import sqlite3
from datetime import datetime
from pathlib import Path
import json

DB_PATH = Path.home() / ".openclaw/workspace/prospecting.db"

class DatabaseManager:
    def __init__(self):
        self.db_path = DB_PATH
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        if not self.db_path.exists():
            print(f"⚠️  DB non trouvée. Initialisation...")
            init_script = Path.home() / ".openclaw/workspace-prospector/scripts/init_db.sql"
            if not init_script.exists():
                init_script = Path.home() / ".openclaw/workspace/scripts/init_db.sql"
            if init_script.exists():
                with open(init_script, 'r') as f:
                    sql = f.read()
                conn = sqlite3.connect(self.db_path)
                conn.executescript(sql)
                conn.close()
                print(f"✅ DB créée: {self.db_path}")
            else:
                print(f"❌ Script init_db.sql non trouvé!")

    def check_duplicate(self, phone_number):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM prospects WHERE phone_number = ?", (phone_number,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def insert_prospect(self, prospect_data):
        if self.check_duplicate(prospect_data['phone_number']):
            print(f"⚠️  Doublon: {prospect_data['phone_number']} ({prospect_data.get('name')})")
            return False
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            website = prospect_data.get('website', '') or ''
            has_website = bool(website) or prospect_data.get('has_website', False)
            cursor.execute("""
                INSERT INTO prospects (
                    phone_number, name, business_name, city, country,
                    type, source, google_maps_url, address, rating,
                    review_count, website, has_website, status, created_at, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                prospect_data['phone_number'],
                prospect_data.get('name'),
                prospect_data.get('business_name', prospect_data.get('name')),
                prospect_data.get('city'),
                prospect_data.get('country'),
                prospect_data.get('type', 'hotel'),
                prospect_data.get('source', 'google_places'),
                prospect_data.get('google_maps_url'),
                prospect_data.get('address'),
                prospect_data.get('rating'),
                prospect_data.get('review_count'),
                website,
                has_website,
                'new',
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            conn.commit()
            website_tag = "🌐" if has_website else "📵"
            print(f"✅ {website_tag} Prospect ajouté: {prospect_data.get('name')} ({prospect_data['phone_number']})")
            return True
        except Exception as e:
            print(f"❌ Erreur insertion: {e}")
            self.log_error('insert_prospect', str(e), json.dumps(prospect_data))
            return False
        finally:
            conn.close()

    def update_status(self, phone_number, new_status, notes=None, method_used=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            now = datetime.now().isoformat()
            if new_status == 'contacted':
                cursor.execute("""
                    UPDATE prospects
                    SET status=?, contacted_at=?, last_updated=?, notes=?
                    """ + (", method_used=?" if method_used else "") + """
                    WHERE phone_number=?
                """, ([new_status, now, now, notes] + ([method_used] if method_used else []) + [phone_number]))
            elif new_status in ('transferred_sandra', 'transferred_nacer'):
                transferred_to = 'sandra' if new_status == 'transferred_sandra' else 'nacer'
                cursor.execute("""
                    UPDATE prospects
                    SET status=?, transferred_at=?, transferred_to=?, last_updated=?, notes=?
                    WHERE phone_number=?
                """, (new_status, now, transferred_to, now, notes, phone_number))
            else:
                cursor.execute("""
                    UPDATE prospects
                    SET status=?, last_updated=?, notes=?
                    WHERE phone_number=?
                """, (new_status, now, notes, phone_number))
            conn.commit()
            print(f"✅ Status: {phone_number} → {new_status}")
        except Exception as e:
            print(f"❌ Erreur update: {e}")
            self.log_error('update_status', str(e), f"phone: {phone_number}, status: {new_status}")
        finally:
            conn.close()

    def get_prospects_to_contact(self, limit=10):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT phone_number, name, city, business_name, country, has_website, website
            FROM prospects
            WHERE status = 'to_contact'
            ORDER BY created_at ASC
            LIMIT ?
        """, (limit,))
        results = cursor.fetchall()
        conn.close()
        return results

    def get_stats(self, date=None):
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT status, COUNT(*) FROM prospects GROUP BY status")
        status_counts = dict(cursor.fetchall())

        cursor.execute("SELECT COUNT(*) FROM prospects WHERE has_website=1")
        with_website = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM prospects WHERE has_website=0 OR has_website IS NULL")
        without_website = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM prospects WHERE DATE(created_at)=?", (date,))
        today_created = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM prospects WHERE DATE(contacted_at)=?", (date,))
        today_contacted = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM prospects WHERE DATE(transferred_at)=? AND transferred_to='sandra'", (date,))
        today_transferred_sandra = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM prospects WHERE DATE(transferred_at)=? AND transferred_to='nacer'", (date,))
        today_transferred_nacer = cursor.fetchone()[0]

        conn.close()
        total = sum(status_counts.values())

        return {
            'date': date,
            'total': total,
            'with_website': with_website,
            'without_website': without_website,
            'status_counts': status_counts,
            'today_created': today_created,
            'today_contacted': today_contacted,
            'today_transferred_sandra': today_transferred_sandra,
            'today_transferred_nacer': today_transferred_nacer
        }

    def log_error(self, error_type, error_message, context):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO errors_log (error_type, error_message, context) VALUES (?, ?, ?)",
            (error_type, error_message, context)
        )
        conn.commit()
        conn.close()

    def update_prospect_response(self, phone_number, sentiment, message_summary=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            now = datetime.now().isoformat()
            note = f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Réponse {sentiment}: {message_summary or 'N/A'}"
            cursor.execute("""
                UPDATE prospects
                SET last_response_at=?, response_sentiment=?,
                    notes=CASE WHEN notes IS NULL THEN ? ELSE notes || '\n' || ? END,
                    last_updated=?
                WHERE phone_number=?
            """, (now, sentiment, note, note, now, phone_number))
            conn.commit()
            print(f"✅ Réponse loggée: {phone_number} - {sentiment}")
        except Exception as e:
            print(f"❌ Erreur log réponse: {e}")
        finally:
            conn.close()


if __name__ == "__main__":
    db = DatabaseManager()
    stats = db.get_stats()
    print(f"\n📊 Stats DB — {stats['date']}")
    print(f"   Total prospects: {stats['total']}")
    print(f"   🌐 Avec site web: {stats['with_website']}")
    print(f"   📵 Sans site web: {stats['without_website']}")
    print(f"   Par statut: {stats['status_counts']}")
    print(f"   Créés aujourd'hui: {stats['today_created']}")
    print(f"   Contactés aujourd'hui: {stats['today_contacted']}")
    print(f"   Transférés Sandra: {stats['today_transferred_sandra']}")
    print(f"   Transférés Nacer: {stats['today_transferred_nacer']}")