#!/usr/bin/env python3
"""
Airtable Sync - Anna Prospection
Synchronisation bi-directionnelle avec Airtable
"""

from pyairtable import Api
import json
from pathlib import Path
from datetime import datetime
from db_manager import DatabaseManager

CREDENTIALS_PATH = Path.home() / ".openclaw/credentials/airtable.json"

class AirtableSync:
    def __init__(self):
        self.db = DatabaseManager()
        self.api = None
        self.table = None
        self._load_credentials()
    
    def _load_credentials(self):
        """Charge les credentials Airtable"""
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
    
    def sync_from_airtable(self):
        """
        Récupère les prospects marqués 'to_contact' dans Airtable
        et les ajoute à la DB locale (avec vérification doublons)
        """
        if not self.table:
            print("❌ Pas de connexion Airtable")
            return 0
        
        print("🔄 Sync depuis Airtable...")
        
        # Récupérer records avec status='to_contact'
        records = self.table.all(formula="{Status}='to_contact'")
        
        added = 0
        for record in records:
            fields = record['fields']
            
            prospect_data = {
                'phone_number': fields.get('Phone'),
                'name': fields.get('Name'),
                'business_name': fields.get('Business Name', fields.get('Name')),
                'city': fields.get('City'),
                'country': fields.get('Country'),
                'type': fields.get('Type', 'hotel').lower(),
                'source': 'airtable',
                'address': fields.get('Address'),
                'notes': fields.get('Notes')
            }
            
            if self.db.insert_prospect(prospect_data):
                self.db.update_status(prospect_data['phone_number'], 'to_contact')
                added += 1
        
        print(f"✅ {added} prospects importés depuis Airtable")
        return added
    
    def sync_to_airtable(self):
        """
        Envoie les prospects 'interested' vers Airtable pour Sandra
        """
        if not self.table:
            print("❌ Pas de connexion Airtable")
            return 0
        
        print("🔄 Sync vers Airtable...")
        
        # Récupérer prospects interested non encore synchro
        conn = self.db.db_path
        import sqlite3
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT phone_number, name, city, country, notes, contacted_at
            FROM prospects 
            WHERE status = 'interested'
        """)
        
        prospects = cursor.fetchall()
        conn.close()
        
        synced = 0
        for prospect in prospects:
            phone, name, city, country, notes, contacted_at = prospect
            
            try:
                self.table.create({
                    'Phone': phone,
                    'Name': name,
                    'City': city,
                    'Country': country,
                    'Status': 'interested',
                    'Notes': notes or '',
                    'Contacted At': contacted_at,
                    'Assigned To': 'Sandra'
                })
                synced += 1
            except Exception as e:
                print(f"⚠️  Erreur sync {name}: {e}")
        
        print(f"✅ {synced} prospects envoyés à Airtable")
        return synced

if __name__ == "__main__":
    sync = AirtableSync()
    
    # Test import
    imported = sync.sync_from_airtable()
    
    # Test export
    exported = sync.sync_to_airtable()
    
    print(f"\n📊 Résumé sync:")
    print(f"   Importés: {imported}")
    print(f"   Exportés: {exported}")
