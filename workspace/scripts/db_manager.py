#!/usr/bin/env python3
"""
Database Manager - Anna Prospection
Gestion de la base de données SQLite pour prospects
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
        """Crée la DB si elle n'existe pas"""
        if not self.db_path.exists():
            print(f"⚠️  Base de données non trouvée. Initialisation...")
            init_script = Path.home() / ".openclaw/workspace/scripts/init_db.sql"
            if init_script.exists():
                with open(init_script, 'r') as f:
                    sql = f.read()
                conn = sqlite3.connect(self.db_path)
                conn.executescript(sql)
                conn.close()
                print(f"✅ Base de données créée: {self.db_path}")
            else:
                print(f"❌ Script init_db.sql non trouvé!")
    
    def check_duplicate(self, phone_number):
        """
        Vérifie si un numéro existe déjà en base
        
        Returns:
            bool: True si doublon, False sinon
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM prospects WHERE phone_number = ?", (phone_number,))
        count = cursor.fetchone()[0]
        
        conn.close()
        return count > 0
    
    def insert_prospect(self, prospect_data):
        """
        Insère un nouveau prospect (avec vérification doublon)
        
        Args:
            prospect_data (dict): {
                'phone_number': '+51XXXXXXXXX',
                'name': 'Hotel Sol',
                'business_name': 'Hotel Sol',
                'city': 'Cusco',
                'country': 'Peru',
                'type': 'hotel',
                'source': 'google_places',
                'google_maps_url': 'https://...',
                'address': 'Av. Sol 123',
                'rating': 4.2,
                'review_count': 87
            }
        
        Returns:
            bool: True si insertion OK, False si doublon
        """
        # Vérifier doublon AVANT insertion
        if self.check_duplicate(prospect_data['phone_number']):
            print(f"⚠️  Doublon: {prospect_data['phone_number']} ({prospect_data.get('name')})")
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO prospects (
                    phone_number, name, business_name, city, country,
                    type, source, google_maps_url, address, rating,
                    review_count, status, created_at, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                'new',
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            print(f"✅ Prospect ajouté: {prospect_data.get('name')} ({prospect_data['phone_number']})")
            return True
            
        except Exception as e:
            print(f"❌ Erreur insertion: {e}")
            self.log_error('insert_prospect', str(e), json.dumps(prospect_data))
            return False
        
        finally:
            conn.close()
    
    def update_status(self, phone_number, new_status, notes=None):
        """
        Met à jour le statut d'un prospect
        
        Args:
            phone_number (str): Numéro du prospect
            new_status (str): new, to_contact, contacted, interested, not_interested, closed
            notes (str): Notes optionnelles
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if new_status == 'contacted':
                cursor.execute("""
                    UPDATE prospects 
                    SET status = ?, contacted_at = ?, last_updated = ?, notes = ?
                    WHERE phone_number = ?
                """, (new_status, datetime.now().isoformat(), datetime.now().isoformat(), notes, phone_number))
            else:
                cursor.execute("""
                    UPDATE prospects 
                    SET status = ?, last_updated = ?, notes = ?
                    WHERE phone_number = ?
                """, (new_status, datetime.now().isoformat(), notes, phone_number))
            
            conn.commit()
            print(f"✅ Status mis à jour: {phone_number} → {new_status}")
            
        except Exception as e:
            print(f"❌ Erreur update: {e}")
            self.log_error('update_status', str(e), f"phone: {phone_number}, status: {new_status}")
        
        finally:
            conn.close()
    
    def get_prospects_to_contact(self, limit=10):
        """
        Récupère les prospects avec status='to_contact'
        
        Returns:
            list: Liste de tuples (phone_number, name, city, business_name)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT phone_number, name, city, business_name, country
            FROM prospects 
            WHERE status = 'to_contact'
            ORDER BY created_at ASC
            LIMIT ?
        """, (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def get_stats(self, date=None):
        """
        Récupère les stats pour une date donnée (ou aujourd'hui)
        
        Returns:
            dict: Stats du jour
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total prospects par statut
        cursor.execute("SELECT status, COUNT(*) FROM prospects GROUP BY status")
        status_counts = dict(cursor.fetchall())
        
        # Prospects créés aujourd'hui
        cursor.execute("""
            SELECT COUNT(*) FROM prospects 
            WHERE DATE(created_at) = ?
        """, (date,))
        today_created = cursor.fetchone()[0]
        
        # Prospects contactés aujourd'hui
        cursor.execute("""
            SELECT COUNT(*) FROM prospects 
            WHERE DATE(contacted_at) = ?
        """, (date,))
        today_contacted = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'date': date,
            'status_counts': status_counts,
            'today_created': today_created,
            'today_contacted': today_contacted,
            'total': sum(status_counts.values())
        }
    
    def log_error(self, error_type, error_message, context):
        """Log une erreur dans la table errors_log"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO errors_log (error_type, error_message, context)
            VALUES (?, ?, ?)
        """, (error_type, error_message, context))
        
        conn.commit()
        conn.close()

if __name__ == "__main__":
    # Test
    db = DatabaseManager()
    stats = db.get_stats()
    print(f"\n📊 Stats de la base:")
    print(f"   Total prospects: {stats['total']}")
    print(f"   Par statut: {stats['status_counts']}")
    print(f"   Créés aujourd'hui: {stats['today_created']}")
    print(f"   Contactés aujourd'hui: {stats['today_contacted']}")
