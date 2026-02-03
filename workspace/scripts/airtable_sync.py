#!/usr/bin/env python3
"""
Airtable Sync - Anna Prospection v2.0
Synchronisation BI-DIRECTIONNELLE avec Airtable
- Évite les doublons (vérification par phone_number)
- Sync status dans les 2 sens
- Ajoute nouveaux prospects des 2 côtés
"""

from pyairtable import Api
import json
from pathlib import Path
from datetime import datetime
import sqlite3

CREDENTIALS_PATH = Path.home() / ".openclaw/credentials/airtable.json"
DB_PATH = Path.home() / ".openclaw/workspace/prospecting.db"

class BidirectionalSync:
    def __init__(self):
        self.db_path = DB_PATH
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
            else:
                print(f"❌ Credentials Airtable invalides")
    
    def log(self, message):
        """Log avec timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def get_airtable_prospects(self):
        """
        Récupère TOUS les prospects d'Airtable
        Returns: dict {phone_number: record_data}
        """
        if not self.table:
            self.log("❌ Pas de connexion Airtable")
            return {}
        
        self.log("📥 Récupération prospects Airtable...")
        
        try:
            records = self.table.all()
            
            prospects_map = {}
            for record in records:
                fields = record['fields']
                phone = fields.get('Phone')
                
                if phone:
                    # Normaliser le numéro (supprimer espaces, tirets)
                    phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
                    
                    prospects_map[phone] = {
                        'record_id': record['id'],
                        'name': fields.get('Name'),
                        'business_name': fields.get('Business Name', fields.get('Name')),
                        'city': fields.get('City'),
                        'country': fields.get('Country'),
                        'type': fields.get('Type', 'hotel').lower(),
                        'status': fields.get('Status', 'new').lower(),
                        'address': fields.get('Address'),
                        'notes': fields.get('Notes'),
                        'contacted_at': fields.get('Contacted At'),
                        'last_response_at': fields.get('Last Response At')
                    }
            
            self.log(f"✅ {len(prospects_map)} prospects récupérés d'Airtable")
            return prospects_map
            
        except Exception as e:
            self.log(f"❌ Erreur récupération Airtable: {e}")
            return {}
    
    def get_local_prospects(self):
        """
        Récupère TOUS les prospects de la DB locale
        Returns: dict {phone_number: record_data}
        """
        self.log("📥 Récupération prospects DB locale...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Permet d'accéder aux colonnes par nom
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    phone_number, name, business_name, city, country,
                    type, status, address, notes, contacted_at,
                    last_response_at, method_used, response_sentiment,
                    rating, review_count, google_maps_url
                FROM prospects
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            prospects_map = {}
            for row in rows:
                phone = row['phone_number']
                # Normaliser
                phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
                
                prospects_map[phone] = {
                    'name': row['name'],
                    'business_name': row['business_name'],
                    'city': row['city'],
                    'country': row['country'],
                    'type': row['type'],
                    'status': row['status'],
                    'address': row['address'],
                    'notes': row['notes'],
                    'contacted_at': row['contacted_at'],
                    'last_response_at': row['last_response_at'],
                    'method_used': row['method_used'],
                    'response_sentiment': row['response_sentiment'],
                    'rating': row['rating'],
                    'review_count': row['review_count'],
                    'google_maps_url': row['google_maps_url']
                }
            
            self.log(f"✅ {len(prospects_map)} prospects récupérés DB locale")
            return prospects_map
            
        except Exception as e:
            self.log(f"❌ Erreur récupération DB locale: {e}")
            return {}
    
    def sync_airtable_to_local(self, airtable_prospects, local_prospects):
        """
        Sync Airtable → DB Locale
        - Ajoute nouveaux prospects
        - Met à jour status si changé
        """
        self.log("\n🔄 SYNC: Airtable → DB Locale")
        
        added = 0
        updated = 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for phone, at_data in airtable_prospects.items():
            try:
                if phone not in local_prospects:
                    # NOUVEAU prospect à ajouter
                    self.log(f"  ➕ Nouveau: {at_data['name']} ({phone})")
                    
                    cursor.execute("""
                        INSERT INTO prospects (
                            phone_number, name, business_name, city, country,
                            type, status, address, notes, contacted_at,
                            last_response_at, source, created_at, last_updated
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        phone,
                        at_data['name'],
                        at_data['business_name'],
                        at_data['city'],
                        at_data['country'],
                        at_data['type'],
                        at_data['status'],
                        at_data['address'],
                        at_data['notes'],
                        at_data['contacted_at'],
                        at_data['last_response_at'],
                        'airtable',
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))
                    added += 1
                
                else:
                    # Prospect EXISTE - Vérifier si status a changé
                    local_status = local_prospects[phone]['status']
                    at_status = at_data['status']
                    
                    if local_status != at_status:
                        # Airtable est la source de vérité si modifié manuellement
                        self.log(f"  🔄 Update status: {at_data['name']} ({local_status} → {at_status})")
                        
                        cursor.execute("""
                            UPDATE prospects 
                            SET status = ?, 
                                notes = CASE 
                                    WHEN notes IS NULL THEN ?
                                    ELSE notes || '\n' || ?
                                END,
                                last_updated = ?
                            WHERE phone_number = ?
                        """, (
                            at_status,
                            f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Status sync depuis Airtable: {at_status}",
                            f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Status sync depuis Airtable: {at_status}",
                            datetime.now().isoformat(),
                            phone
                        ))
                        updated += 1
            
            except Exception as e:
                self.log(f"  ❌ Erreur sync {phone}: {e}")
        
        conn.commit()
        conn.close()
        
        self.log(f"✅ Ajoutés: {added} | Mis à jour: {updated}")
        return added, updated
    
    def sync_local_to_airtable(self, local_prospects, airtable_prospects):
        """
        Sync DB Locale → Airtable
        - Ajoute nouveaux prospects
        - Met à jour status si changé (priorité à la DB locale car Anna travaille dessus)
        """
        if not self.table:
            self.log("❌ Pas de connexion Airtable")
            return 0, 0
        
        self.log("\n🔄 SYNC: DB Locale → Airtable")
        
        added = 0
        updated = 0
        
        for phone, local_data in local_prospects.items():
            try:
                if phone not in airtable_prospects:
                    # NOUVEAU prospect à ajouter sur Airtable
                    self.log(f"  ➕ Nouveau: {local_data['name']} ({phone})")
                    
                    # Créer le record Airtable
                    self.table.create({
                        'Phone': phone,
                        'Name': local_data['name'],
                        'Business Name': local_data['business_name'],
                        'City': local_data['city'],
                        'Country': local_data['country'],
                        'Type': local_data['type'].capitalize(),
                        'Status': local_data['status'],
                        'Address': local_data['address'] or '',
                        'Notes': local_data['notes'] or '',
                        'Contacted At': local_data['contacted_at'],
                        'Last Response At': local_data['last_response_at'],
                        'Method Used': local_data['method_used'] or '',
                        'Response Sentiment': local_data['response_sentiment'] or '',
                        'Rating': local_data['rating'],
                        'Review Count': local_data['review_count'],
                        'Google Maps URL': local_data['google_maps_url'] or ''
                    })
                    added += 1
                
                else:
                    # Prospect EXISTE - La DB locale a priorité sur le status (Anna travaille dessus)
                    local_status = local_data['status']
                    at_status = airtable_prospects[phone]['status']
                    record_id = airtable_prospects[phone]['record_id']
                    
                    if local_status != at_status:
                        self.log(f"  🔄 Update status: {local_data['name']} ({at_status} → {local_status})")
                        
                        # Mettre à jour Airtable avec les infos de la DB locale
                        self.table.update(record_id, {
                            'Status': local_status,
                            'Contacted At': local_data['contacted_at'],
                            'Last Response At': local_data['last_response_at'],
                            'Method Used': local_data['method_used'] or '',
                            'Response Sentiment': local_data['response_sentiment'] or '',
                            'Notes': local_data['notes'] or ''
                        })
                        updated += 1
            
            except Exception as e:
                self.log(f"  ❌ Erreur sync {phone}: {e}")
        
        self.log(f"✅ Ajoutés: {added} | Mis à jour: {updated}")
        return added, updated
    
    def run_full_sync(self):
        """
        Exécute la synchronisation complète bidirectionnelle
        """
        self.log("="*70)
        self.log("🔄 SYNCHRONISATION BIDIRECTIONNELLE AIRTABLE ↔ DB LOCALE")
        self.log("="*70)
        
        if not self.table:
            self.log("❌ Impossible de synchroniser sans connexion Airtable")
            return
        
        # 1. Récupérer les données des 2 côtés
        airtable_prospects = self.get_airtable_prospects()
        local_prospects = self.get_local_prospects()
        
        # 2. Sync Airtable → Local (nouveaux prospects + updates status)
        at_to_local_added, at_to_local_updated = self.sync_airtable_to_local(
            airtable_prospects, 
            local_prospects
        )
        
        # 3. Sync Local → Airtable (nouveaux prospects + updates status)
        # IMPORTANT: On recharge local_prospects pour avoir les ajouts du step 2
        local_prospects = self.get_local_prospects()
        local_to_at_added, local_to_at_updated = self.sync_local_to_airtable(
            local_prospects,
            airtable_prospects
        )
        
        # 4. Résumé
        self.log("\n" + "="*70)
        self.log("📊 RÉSUMÉ SYNCHRONISATION")
        self.log("="*70)
        self.log(f"Airtable → DB Locale:")
        self.log(f"  ➕ Ajoutés: {at_to_local_added}")
        self.log(f"  🔄 Mis à jour: {at_to_local_updated}")
        self.log(f"\nDB Locale → Airtable:")
        self.log(f"  ➕ Ajoutés: {local_to_at_added}")
        self.log(f"  🔄 Mis à jour: {local_to_at_updated}")
        self.log("="*70)
        
        return {
            'airtable_to_local': {'added': at_to_local_added, 'updated': at_to_local_updated},
            'local_to_airtable': {'added': local_to_at_added, 'updated': local_to_at_updated}
        }


if __name__ == "__main__":
    sync = BidirectionalSync()
    sync.run_full_sync()
