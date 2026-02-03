#!/usr/bin/env python3
"""
Google Places Scraper v2 - Dynamique
Accepte n'importe quelle ville en paramètre
"""

import googlemaps
import json
import time
import sys
from datetime import datetime
from pathlib import Path
from db_manager import DatabaseManager

CREDENTIALS_PATH = Path.home() / ".openclaw/credentials/google_places.json"
LOG_PATH = Path.home() / f".openclaw/workspace/memory/prospecting_{datetime.now().strftime('%Y-%m-%d')}.md"

class GooglePlacesScraper:
    def __init__(self):
        self.db = DatabaseManager()
        self.api_key = self._load_api_key()
        self.gmaps = googlemaps.Client(key=self.api_key) if self.api_key else None
        self.api_calls = 0
    
    def _load_api_key(self):
        if not CREDENTIALS_PATH.exists():
            print(f"❌ Fichier credentials non trouvé: {CREDENTIALS_PATH}")
            return None
        
        with open(CREDENTIALS_PATH, 'r') as f:
            creds = json.load(f)
            return creds.get('api_key')
    
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        print(log_entry.strip())
        
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    
    def search_city_by_name(self, city_name, country_name=None, max_results=20):
        """
        Recherche dynamique par nom de ville (NOUVEAU)
        
        Args:
            city_name: "Mexico DF", "Arequipa", "Bogota", etc.
            country_name: "Mexico", "Peru", "Colombia" (optionnel)
            max_results: Nombre max de résultats
        """
        if not self.gmaps:
            self.log("❌ Pas de client Google Maps configuré")
            return []
        
        # Construire la requête de recherche
        location_query = f"{city_name}, {country_name}" if country_name else city_name
        
        self.log(f"🔍 Recherche à {location_query}")
        
        prospects_found = []
        
        try:
            # Text Search pour obtenir les établissements
            query = f"hotel hostel hospedaje {location_query}"
            results = self.gmaps.places(query=query, language='es')
            self.api_calls += 1
            
            places = results.get('results', [])
            self.log(f"📊 {len(places)} établissements trouvés")
            
            for place in places[:max_results]:
                if place.get('website'):
                    continue
                
                place_id = place.get('place_id')
                details = self.gmaps.place(
                    place_id,
                    fields=['name','formatted_phone_number','website','formatted_address','rating','user_ratings_total','geometry']
                )
                self.api_calls += 1
                
                result = details.get('result', {})
                
                # Filtres
                if result.get('website'):
                    continue
                
                phone = result.get('formatted_phone_number')
                if not phone:
                    continue
                
                # Détecter le pays depuis l'adresse si non fourni
                address = result.get('formatted_address', '')
                if not country_name:
                    country_name = self._detect_country(address)
                
                # Normaliser téléphone
                phone = self._normalize_phone(phone, country_name)
                
                prospect = {
                    'phone_number': phone,
                    'name': result.get('name'),
                    'business_name': result.get('name'),
                    'city': city_name,
                    'country': country_name,
                    'type': self._detect_type(result.get('name', '')),
                    'source': 'google_places',
                    'google_maps_url': f"https://www.google.com/maps/place/?q=place_id:{place_id}",
                    'address': address,
                    'rating': result.get('rating'),
                    'review_count': result.get('user_ratings_total')
                }
                
                prospects_found.append(prospect)
                time.sleep(0.5)
            
            self.log(f"✅ {len(prospects_found)} prospects sans website trouvés")
            
        except Exception as e:
            self.log(f"❌ Erreur recherche {location_query}: {e}")
            self.db.log_error('google_places_search', str(e), location_query)
        
        return prospects_found
    
    def _detect_country(self, address):
        """Détecte le pays depuis l'adresse"""
        countries = {
            'Mexico': ['México', 'Mexico'],
            'Peru': ['Perú', 'Peru'],
            'Bolivia': ['Bolivia'],
            'Ecuador': ['Ecuador'],
            'Colombia': ['Colombia'],
            'Chile': ['Chile'],
            'Argentina': ['Argentina']
        }
        
        for country, keywords in countries.items():
            for keyword in keywords:
                if keyword in address:
                    return country
        
        return 'Unknown'
    
    def _normalize_phone(self, phone, country):
        phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        country_codes = {
            'Peru': '+51',
            'Bolivia': '+591',
            'Ecuador': '+593',
            'Colombia': '+57',
            'Chile': '+56',
            'Argentina': '+54',
            'Mexico': '+52'
        }
        
        if not phone.startswith('+'):
            code = country_codes.get(country, '+51')
            phone = code + phone.lstrip('0')
        
        return phone
    
    def _detect_type(self, name):
        name_lower = name.lower()
        
        if 'hostel' in name_lower or 'hostal' in name_lower:
            return 'hostel'
        elif 'lodge' in name_lower:
            return 'lodge'
        elif 'tour' in name_lower or 'agencia' in name_lower:
            return 'tour_operator'
        else:
            return 'hotel'
    
    def run_dynamic(self, city_name, country_name=None, max_results=20):
        """
        Point d'entrée dynamique (NOUVEAU)
        Permet de chercher N'IMPORTE quelle ville
        """
        self.log("="*60)
        self.log(f"🚀 SCRAPING DYNAMIQUE: {city_name}")
        self.log("="*60)
        
        prospects = self.search_city_by_name(city_name, country_name, max_results)
        
        added = 0
        for prospect in prospects:
            if self.db.insert_prospect(prospect):
                self.db.update_status(prospect['phone_number'], 'to_contact')
                added += 1
        
        self.log("="*60)
        self.log(f"✅ SCRAPING TERMINÉ")
        self.log(f"📊 Prospects trouvés: {len(prospects)}")
        self.log(f"📊 Prospects ajoutés: {added}")
        self.log(f"📊 Appels API: {self.api_calls}")
        self.log("="*60)
        
        return added

# CLI pour usage direct
if __name__ == "__main__":
    scraper = GooglePlacesScraper()
    
    if len(sys.argv) >= 2:
        city = sys.argv[1]
        country = sys.argv[2] if len(sys.argv) >= 3 else None
        max_res = int(sys.argv[3]) if len(sys.argv) >= 4 else 20
        
        scraper.run_dynamic(city, country, max_res)
    else:
        print("Usage: python3 google_places_scraper.py <ville> [pays] [max_results]")
        print("Exemple: python3 google_places_scraper.py 'Mexico DF' Mexico 10")
