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
        """
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
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT status, COUNT(*) FROM prospects GROUP BY status")
        status_counts = dict(cursor.fetchall())
        
        cursor.execute("""
            SELECT COUNT(*) FROM prospects 
            WHERE DATE(created_at) = ?
        """, (date,))
        today_created = cursor.fetchone()[0]
        
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

    # ============================
    # NOUVELLES MÉTHODES AJOUTÉES
    # ============================

    def update_method_stats(self, method_name, action):
        """
        Met à jour les stats d'une méthode
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if action == 'sent':
                cursor.execute("""
                    UPDATE method_stats 
                    SET total_sent = total_sent + 1,
                        last_updated = ?
                    WHERE method_name = ?
                """, (datetime.now().isoformat(), method_name))
            
            elif action == 'responded':
                cursor.execute("""
                    UPDATE method_stats 
                    SET responded = responded + 1,
                        conversion_rate = (responded * 1.0 / total_sent),
                        last_updated = ?
                    WHERE method_name = ?
                """, (datetime.now().isoformat(), method_name))
            
            elif action == 'interested':
                cursor.execute("""
                    UPDATE method_stats 
                    SET interested = interested + 1,
                        conversion_rate = (interested * 1.0 / total_sent),
                        last_updated = ?
                    WHERE method_name = ?
                """, (datetime.now().isoformat(), method_name))
            
            conn.commit()
            print(f"✅ Stats méthode {method_name} mises à jour: {action}")
            
        except Exception as e:
            print(f"❌ Erreur update stats: {e}")
            self.log_error('update_method_stats', str(e), f"method: {method_name}, action: {action}")
        
        finally:
            conn.close()

    def get_best_method(self):
        """Retourne la méthode avec le meilleur taux de conversion"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT method_name, conversion_rate 
            FROM method_stats 
            WHERE total_sent > 0
            ORDER BY conversion_rate DESC 
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {'method': result[0], 'conversion_rate': result[1]}
        return None

    def update_prospect_response(self, phone_number, sentiment, message_summary=None):
        """
        Log une réponse de prospect
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE prospects 
                SET last_response_at = ?,
                    response_sentiment = ?,
                    notes = CASE 
                        WHEN notes IS NULL THEN ?
                        ELSE notes || '\n' || ?
                    END,
                    last_updated = ?
                WHERE phone_number = ?
            """, (
                datetime.now().isoformat(),
                sentiment,
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Réponse {sentiment}: {message_summary or 'N/A'}",
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Réponse {sentiment}: {message_summary or 'N/A'}",
                datetime.now().isoformat(),
                phone_number
            ))
            
            cursor.execute(
                "SELECT method_used FROM prospects WHERE phone_number = ?",
                (phone_number,)
            )
            result = cursor.fetchone()
            
            if result and result[0]:
                cursor.execute("""
                    UPDATE method_stats 
                    SET responded = responded + 1,
                        conversion_rate = (interested * 1.0 / total_sent)
                    WHERE method_name = ?
                """, (result[0],))
            
            conn.commit()
            print(f"✅ Réponse loggée: {phone_number} - {sentiment}")
            
        except Exception as e:
            print(f"❌ Erreur log réponse: {e}")
            self.log_error(
                'update_prospect_response',
                str(e),
                f"phone: {phone_number}, sentiment: {sentiment}"
            )
        
        finally:
            conn.close()


if __name__ == "__main__":
    db = DatabaseManager()
    stats = db.get_stats()
    print(f"\n📊 Stats de la base:")
    print(f"   Total prospects: {stats['total']}")
    print(f"   Par statut: {stats['status_counts']}")
    print(f"   Créés aujourd'hui: {stats['today_created']}")
    print(f"   Contactés aujourd'hui: {stats['today_contacted']}")
