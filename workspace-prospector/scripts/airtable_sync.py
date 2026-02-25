#!/usr/bin/env python3
"""
Airtable Sync v3 - Synchronisation bidirectionnelle
Nouveautés:
- Champ "Site web" synchronisé
- Champ "has_website" pris en compte
- Support transferts Sandra/Nacer
"""

from pyairtable import Api
import json
from pathlib import Path
from datetime import datetime
import sqlite3

CREDENTIALS_PATH = Path.home() / ".openclaw/credentials/airtable.json"
DB_PATH = Path.home() / ".openclaw/workspace/prospecting.db"

STATUS_MAPPING = {
    'new': 'new',
    'to_contact': 'to_contact',
    'contacted': 'contacted',
    'interested': 'interested',
    'responded_positive': 'contacted',
    'responded_neutral': 'contacted',
    'responded_negative': 'rejected',
    'no_response': 'contacted',
    'not_interested': 'rejected',
    'transferred_sandra': 'client',
    'transferred_nacer': 'interested',
    'closed_won': 'client',
    'closed_lost': 'rejected',
    'qualified': 'interested'
}

class BidirectionalSync:
    def __init__(self):
        self.db_path = DB_PATH
        self.api = None
        self.table = None
        self._load_credentials()

    def _load_credentials(self):
        if not CREDENTIALS_PATH.exists():
            print(f"❌ Credentials Airtable non trouvés: {CREDENTIALS_PATH}")
            return
        with open(CREDENTIALS_PATH, 'r') as f:
            creds = json.load(f)
            api_key = creds.get('api_key')
            base_id = creds.get('base_id')
            if api_key and base_id:
                self.api = Api(api_key)
                self.table = self.api.table(base_id, 'Prospects')
                print(f"✅ Connecté à Airtable")
            else:
                print(f"❌ Credentials Airtable invalides")

    def _map_status(self, local_status):
        return STATUS_MAPPING.get(local_status, 'new')

    def log(self, message):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

    def get_airtable_prospects(self):
        if not self.table:
            return {}
        self.log("📥 Récupération prospects Airtable...")
        try:
            records = self.table.all()
            prospects_map = {}
            for record in records:
                fields = record['fields']
                phone = fields.get('Phone', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
                if phone:
                    prospects_map[phone] = {
                        'record_id': record['id'],
                        'name': fields.get('Name'),
                        'city': fields.get('City'),
                        'status': fields.get('Status', 'new').lower(),
                        'website': fields.get('Site web', ''),
                        'created_at': fields.get('Created At')
                    }
            self.log(f"✅ {len(prospects_map)} prospects Airtable")
            return prospects_map
        except Exception as e:
            self.log(f"❌ Erreur Airtable: {e}")
            return {}

    def get_local_prospects(self):
        self.log("📥 Récupération prospects DB locale...")
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT phone_number, name, business_name, city, country,
                       type, status, address, notes, contacted_at,
                       last_response_at, method_used, response_sentiment,
                       rating, review_count, google_maps_url, website, has_website
                FROM prospects
            """)
            rows = cursor.fetchall()
            conn.close()
            prospects_map = {}
            for row in rows:
                phone = row['phone_number'].replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
                prospects_map[phone] = dict(row)
            self.log(f"✅ {len(prospects_map)} prospects DB locale")
            return prospects_map
        except Exception as e:
            self.log(f"❌ Erreur DB locale: {e}")
            return {}

    def sync_local_to_airtable(self, local_prospects, airtable_prospects):
        if not self.table:
            return 0, 0
        self.log("\n🔄 SYNC: DB Locale → Airtable")
        added = 0
        updated = 0

        for phone, local_data in local_prospects.items():
            try:
                airtable_status = self._map_status(local_data['status'])
                website = local_data.get('website') or ''

                if phone not in airtable_prospects:
                    self.log(f"  ➕ Nouveau: {local_data['name']} ({phone})")
                    fields = {
                        'Phone': phone,
                        'Name': local_data['name'] or '',
                        'City': local_data.get('city') or '',
                        'Status': airtable_status,
                    }
                    if website:
                        fields['Site web'] = website
                    self.table.create(fields)
                    added += 1
                else:
                    record_id = airtable_prospects[phone]['record_id']
                    at_status = airtable_prospects[phone]['status']
                    at_website = airtable_prospects[phone].get('website', '')
                    updates = {}

                    if airtable_status != at_status:
                        self.log(f"  🔄 Status: {local_data['name']} ({at_status} → {airtable_status})")
                        updates['Status'] = airtable_status

                    if website and website != at_website:
                        updates['Site web'] = website

                    if updates:
                        self.table.update(record_id, updates)
                        updated += 1

            except Exception as e:
                self.log(f"  ❌ Erreur sync {phone}: {e}")

        self.log(f"✅ Ajoutés: {added} | Mis à jour: {updated}")
        return added, updated

    def sync_airtable_to_local(self, airtable_prospects, local_prospects):
        self.log("\n🔄 SYNC: Airtable → DB Locale")
        added = 0
        updated = 0
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for phone, at_data in airtable_prospects.items():
            try:
                if phone not in local_prospects:
                    self.log(f"  ➕ Nouveau depuis Airtable: {at_data['name']} ({phone})")
                    cursor.execute("""
                        INSERT INTO prospects (
                            phone_number, name, business_name, city,
                            status, website, has_website, source, created_at, last_updated
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        phone, at_data['name'], at_data['name'],
                        at_data.get('city'), at_data['status'],
                        at_data.get('website', ''),
                        bool(at_data.get('website', '')),
                        'airtable',
                        at_data.get('created_at') or datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))
                    added += 1
                else:
                    local_status = local_prospects[phone]['status']
                    at_status = at_data['status']
                    if local_status != at_status:
                        self.log(f"  🔄 Status Airtable→Local: {at_data['name']} ({local_status} → {at_status})")
                        cursor.execute(
                            "UPDATE prospects SET status=?, last_updated=? WHERE phone_number=?",
                            (at_status, datetime.now().isoformat(), phone)
                        )
                        updated += 1

            except Exception as e:
                self.log(f"  ❌ Erreur sync {phone}: {e}")

        conn.commit()
        conn.close()
        self.log(f"✅ Ajoutés: {added} | Mis à jour: {updated}")
        return added, updated

    def run_full_sync(self):
        self.log("=" * 70)
        self.log("🔄 SYNCHRONISATION BIDIRECTIONNELLE AIRTABLE ↔ DB LOCALE")
        self.log("=" * 70)

        if not self.table:
            self.log("❌ Impossible de synchroniser sans connexion Airtable")
            return

        airtable_prospects = self.get_airtable_prospects()
        local_prospects = self.get_local_prospects()

        at_added, at_updated = self.sync_airtable_to_local(airtable_prospects, local_prospects)
        local_prospects = self.get_local_prospects()
        l_added, l_updated = self.sync_local_to_airtable(local_prospects, airtable_prospects)

        self.log("\n" + "=" * 70)
        self.log("📊 RÉSUMÉ")
        self.log(f"  Airtable→Local: +{at_added} ajoutés, {at_updated} mis à jour")
        self.log(f"  Local→Airtable: +{l_added} ajoutés, {l_updated} mis à jour")
        self.log("=" * 70)

        return {
            'airtable_to_local': {'added': at_added, 'updated': at_updated},
            'local_to_airtable': {'added': l_added, 'updated': l_updated}
        }


if __name__ == "__main__":
    sync = BidirectionalSync()
    sync.run_full_sync()