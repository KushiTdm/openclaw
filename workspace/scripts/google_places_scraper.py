#!/usr/bin/env python3
"""
Google Places Scraper - Anna Prospection
Recherche d'établissements sans website via Google Places API
"""

import googlemaps
import json
import time
from datetime import datetime
from pathlib import Path
from db_manager import DatabaseManager

# Chemins
CREDENTIALS_PATH = Path.home() / ".openclaw/credentials/google_places.json"
LOG_PATH = Path.home() / f".openclaw/workspace/memory/prospecting_{datetime.now().strftime('%Y-%m-%d')}.md"

# Villes cibles
CITIES = [
    {"name": "Cusco", "country": "Peru", "coords": (-13.5319, -71.9675)},
    {"name": "Lima", "country": "Peru", "coords": (-12.0464, -77.0428)},
    {"name": "Arequipa", "country": "Peru", "coords": (-16.4090, -71.5375)},
    {"name": "Sucre", "country": "Bolivia", "coords": (-19.0472, -65.2623)},
    {"name": "La Paz", "country": "Bolivia", "coords": (-16.5000, -68.1500)},
    {"name": "Quito", "country": "Ecuador", "coords": (-0.1807, -78.4678)},
]

class GooglePlacesScraper:
    def __init__(self):
        self.db = DatabaseManager()
        self.api_key = self._load_api_key()
        self.gmaps = googlemaps.Client(key=self.api_key) if self.api_key else None
        self.api_calls = 0
    
    def _load_api_key(self):
        """Charge la clé API depuis credentials"""
        if not CREDENTIALS_PATH.exists():
            print(f"❌ Fichier credentials non trouvé: {CREDENTIALS_PATH}")
            return None
        
        with open(CREDENTIALS_PATH, 'r') as f:
            creds = json.load(f)
            return creds.get('api_key')
    
    def log(self, message):
        """Log dans le fichier quotidien"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        print(log_entry.strip())
        
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    
    def search_city(self, city_data, max_results=20):
        """
        Recherche dans une ville
        
        Stratégie optimisée:
        1. Text Search (1 requête) pour avoir aperçu
        2. Place Details UNIQUEMENT si 'website' absent
        """
        if not self.gmaps:
            self.log("❌ Pas de client Google Maps configuré")
            return []
        
        self.log(f"🔍 Recherche à {city_data['name']}, {city_data['country']}")
        
        prospects_found = []
        
        try:
            # Text Search (1 requête = 32$ pour 1000)
            query = f"hotel hostel hospedaje {city_data['name']}"
            results = self.gmaps.places(query=query, language='es')
            self.api_calls += 1
            
            places = results.get('results', [])
            self.log(f"📊 {len(places)} établissements trouvés")
            
            for place in places[:max_results]:
                # Si 'website' déjà dans résultat initial, skip
                if place.get('website'):
                    continue
                
                # Place Details seulement si pas de website (17$ pour 1000)
                place_id = place.get('place_id')
                details = self.gmaps.place(
                    place_id, 
                    fields=['name','formatted_phone_number','website','formatted_address','rating','user_ratings_total']
                )
                self.api_calls += 1
                
                result = details.get('result', {})
                
                # Filtrer: PAS de website
                if result.get('website'):
                    continue
                
                # Filtrer: DOIT avoir un téléphone
                phone = result.get('formatted_phone_number')
                if not phone:
                    continue
                
                # Normaliser le téléphone
                phone = self._normalize_phone(phone, city_data['country'])
                
                prospect = {
                    'phone_number': phone,
                    'name': result.get('name'),
                    'business_name': result.get('name'),
                    'city': city_data['name'],
                    'country': city_data['country'],
                    'type': self._detect_type(result.get('name', '')),
                    'source': 'google_places',
                    'google_maps_url': f"https://www.google.com/maps/place/?q=place_id:{place_id}",
                    'address': result.get('formatted_address'),
                    'rating': result.get('rating'),
                    'review_count': result.get('user_ratings_total')
                }
                
                prospects_found.append(prospect)
                
                # Rate limiting (éviter ban)
                time.sleep(0.5)
            
            self.log(f"✅ {len(prospects_found)} prospects sans website trouvés")
            
        except Exception as e:
            self.log(f"❌ Erreur recherche {city_data['name']}: {e}")
            self.db.log_error('google_places_search', str(e), json.dumps(city_data))
        
        return prospects_found
    
    def _normalize_phone(self, phone, country):
        """Normalise un numéro de téléphone"""
        # Nettoyer
        phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        # Ajouter indicatif pays si manquant
        country_codes = {
            'Peru': '+51',
            'Bolivia': '+591',
            'Ecuador': '+593',
            'Colombia': '+57',
            'Chile': '+56',
            'Argentina': '+54'
        }
        
        if not phone.startswith('+'):
            code = country_codes.get(country, '+51')
            phone = code + phone.lstrip('0')
        
        return phone
    
    def _detect_type(self, name):
        """Détecte le type d'établissement depuis le nom"""
        name_lower = name.lower()
        
        if 'hostel' in name_lower or 'hostal' in name_lower:
            return 'hostel'
        elif 'lodge' in name_lower:
            return 'lodge'
        elif 'tour' in name_lower or 'agencia' in name_lower:
            return 'tour_operator'
        else:
            return 'hotel'
    
    def run(self, cities=None, max_per_city=20):
        """
        Lance le scraping sur plusieurs villes
        
        Args:
            cities (list): Liste de villes (ou None pour CITIES par défaut)
            max_per_city (int): Max prospects par ville
        """
        if not cities:
            cities = CITIES
        
        self.log("="*60)
        self.log("🚀 DÉMARRAGE SCRAPING GOOGLE PLACES")
        self.log("="*60)
        
        total_found = 0
        total_added = 0
        
        for city in cities:
            prospects = self.search_city(city, max_results=max_per_city)
            
            for prospect in prospects:
                if self.db.insert_prospect(prospect):
                    total_added += 1
                    # Marquer comme 'to_contact' immédiatement
                    self.db.update_status(prospect['phone_number'], 'to_contact')
            
            total_found += len(prospects)
            
            # Pause entre villes
            time.sleep(2)
        
        self.log("="*60)
        self.log(f"✅ SCRAPING TERMINÉ")
        self.log(f"📊 Prospects trouvés: {total_found}")
        self.log(f"📊 Prospects ajoutés: {total_added}")
        self.log(f"📊 Doublons évités: {total_found - total_added}")
        self.log(f"📊 Appels API Google: {self.api_calls}")
        self.log("="*60)
        
        return total_added

if __name__ == "__main__":
    scraper = GooglePlacesScraper()
    
    # Scraper 1 ville pour test (limite 10 prospects)
    added = scraper.run(cities=[CITIES[0]], max_per_city=10)
    
    print(f"\n📊 Résumé:")
    print(f"   Prospects ajoutés: {added}")
    print(f"   Appels API: {scraper.api_calls}")
    
    # Stats DB
    stats = scraper.db.get_stats()
    print(f"   Total en DB: {stats['total']}")
