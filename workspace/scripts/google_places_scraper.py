#!/usr/bin/env python3
"""
Google Places Scraper v3 - UNIVERSEL
Accepte N'IMPORTE quelle ville/pays du monde
Utilise Brave Search si infos manquantes
"""

import googlemaps
import requests
import json
import time
import sys
from datetime import datetime
from pathlib import Path
from db_manager import DatabaseManager

CREDENTIALS_PATH = Path.home() / ".openclaw/credentials/google_places.json"
BRAVE_CREDENTIALS = Path.home() / ".openclaw/credentials/brave.json"
LOG_PATH = Path.home() / f".openclaw/workspace/memory/prospecting_{datetime.now().strftime('%Y-%m-%d')}.md"

class UniversalScraper:
    def __init__(self):
        self.db = DatabaseManager()
        
        # Google Places API
        self.api_key = self._load_google_key()
        self.gmaps = googlemaps.Client(key=self.api_key) if self.api_key else None
        
        # Brave Search API
        self.brave_key = self._load_brave_key()
        
        self.api_calls = 0
    
    def _load_google_key(self):
        if CREDENTIALS_PATH.exists():
            with open(CREDENTIALS_PATH, 'r') as f:
                return json.load(f).get('api_key')
        return None
    
    def _load_brave_key(self):
        if BRAVE_CREDENTIALS.exists():
            with open(BRAVE_CREDENTIALS, 'r') as f:
                return json.load(f).get('api_key')
        return None
    
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        print(log_entry.strip())
        
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    
    def get_country_code_universal(self, country_name):
        """
        Obtient l'indicatif téléphonique UNIVERSEL via Brave Search
        
        Args:
            country_name: "Japan", "Brasil", "Thailand", etc.
        
        Returns:
            str: "+81", "+55", "+66", etc.
        """
        if not self.brave_key:
            self.log("⚠️  Brave API non configurée - Utilisation codes par défaut")
            return self._get_default_code(country_name)
        
        try:
            # Recherche Brave pour indicatif
            query = f"{country_name} country calling code phone"
            
            headers = {
                'Accept': 'application/json',
                'X-Subscription-Token': self.brave_key
            }
            
            params = {'q': query, 'count': 3}
            
            response = requests.get(
                'https://api.search.brave.com/res/v1/web/search',
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Parser les résultats pour extraire l'indicatif
                for result in data.get('web', {}).get('results', []):
                    text = result.get('description', '') + result.get('title', '')
                    
                    # Chercher pattern "+XX" dans le texte
                    import re
                    matches = re.findall(r'\+\d{1,4}', text)
                    
                    if matches:
                        code = matches[0]
                        self.log(f"✅ Code trouvé via Brave: {country_name} = {code}")
                        return code
            
            # Fallback si Brave échoue
            return self._get_default_code(country_name)
            
        except Exception as e:
            self.log(f"⚠️  Erreur Brave Search: {e}")
            return self._get_default_code(country_name)
    
    def _get_default_code(self, country_name):
        """Codes par défaut pour pays courants"""
        defaults = {
            'Mexico': '+52', 'Peru': '+51', 'Bolivia': '+591',
            'Ecuador': '+593', 'Colombia': '+57', 'Chile': '+56',
            'Argentina': '+54', 'Brazil': '+55', 'Brasil': '+55',
            'USA': '+1', 'United States': '+1', 'Canada': '+1',
            'Spain': '+34', 'France': '+33', 'UK': '+44',
            'Japan': '+81', 'China': '+86', 'Thailand': '+66',
            'Vietnam': '+84', 'Indonesia': '+62', 'Malaysia': '+60'
        }
        
        for key, code in defaults.items():
            if key.lower() in country_name.lower():
                return code
        
        # Fallback ultime
        self.log(f"⚠️  Code inconnu pour {country_name} - Utilisation +1 par défaut")
        return '+1'
    
    def detect_country_from_address(self, address):
        """
        Détecte le pays depuis une adresse (UNIVERSEL)
        
        Args:
            address: "123 Main St, Tokyo, Japan"
        
        Returns:
            str: "Japan"
        """
        # Extraire le dernier mot (souvent le pays)
        parts = address.split(',')
        if len(parts) >= 2:
            potential_country = parts[-1].strip()
            
            # Nettoyer les codes postaux
            import re
            potential_country = re.sub(r'\d+', '', potential_country).strip()
            
            if len(potential_country) > 2:  # Nom de pays valide
                return potential_country
        
        return 'Unknown'
    
    def normalize_phone_universal(self, phone, country_name):
        """
        Normalise un numéro pour N'IMPORTE quel pays
        
        Args:
            phone: "03-1234-5678", "11987654321", etc.
            country_name: "Japan", "Brazil", etc.
        
        Returns:
            str: "+813XXXXXXXX", "+5511XXXXXXXX", etc.
        """
        # Nettoyer
        phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('.', '')
        
        # Si déjà internationalisé, garder tel quel
        if phone.startswith('+'):
            return phone
        
        # Obtenir l'indicatif pays
        country_code = self.get_country_code_universal(country_name)
        
        # Retirer les 0 initiaux (format local)
        phone = phone.lstrip('0')
        
        return country_code + phone
    
    def search_city_universal(self, city_name, country_name=None, max_results=20):
        """
        Recherche UNIVERSELLE - Fonctionne partout dans le monde
        
        Args:
            city_name: "Tokyo", "São Paulo", "Bangkok", etc.
            country_name: "Japan", "Brazil", "Thailand" (optionnel)
            max_results: Max de résultats
        """
        if not self.gmaps:
            self.log("❌ Google Maps API non configurée")
            return []
        
        # Construire requête
        location_query = f"{city_name}, {country_name}" if country_name else city_name
        
        self.log(f"🔍 Recherche UNIVERSELLE à {location_query}")
        
        prospects_found = []
        
        try:
            # Text Search Google Places
            query = f"hotel hostel accommodation {location_query}"
            results = self.gmaps.places(query=query, language='en')  # Anglais = universel
            self.api_calls += 1
            
            places = results.get('results', [])
            self.log(f"📊 {len(places)} établissements trouvés")
            
            for place in places[:max_results]:
                if place.get('website'):
                    continue
                
                place_id = place.get('place_id')
                details = self.gmaps.place(
                    place_id,
                    fields=['name','international_phone_number','formatted_phone_number','website','formatted_address','rating','user_ratings_total']
                )
                self.api_calls += 1
                
                result = details.get('result', {})
                
                if result.get('website'):
                    continue
                
                # Téléphone (préférer international_phone_number)
                phone = result.get('international_phone_number') or result.get('formatted_phone_number')
                
                if not phone:
                    continue
                
                # Détecter pays depuis adresse
                address = result.get('formatted_address', '')
                detected_country = country_name or self.detect_country_from_address(address)
                
                # Normaliser téléphone
                phone = self.normalize_phone_universal(phone, detected_country)
                
                prospect = {
                    'phone_number': phone,
                    'name': result.get('name'),
                    'business_name': result.get('name'),
                    'city': city_name,
                    'country': detected_country,
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
    
    def _detect_type(self, name):
        name_lower = name.lower()
        
        if any(word in name_lower for word in ['hostel', 'hostal', 'backpack', 'dormitory']):
            return 'hostel'
        elif any(word in name_lower for word in ['lodge', 'resort', 'villa']):
            return 'lodge'
        elif any(word in name_lower for word in ['tour', 'travel', 'agency', 'agencia']):
            return 'tour_operator'
        else:
            return 'hotel'
    
    def run(self, city_name, country_name=None, max_results=20):
        """Point d'entrée principal"""
        self.log("="*60)
        self.log(f"🚀 SCRAPING UNIVERSEL: {city_name}")
        if country_name:
            self.log(f"   Pays spécifié: {country_name}")
        self.log("="*60)
        
        prospects = self.search_city_universal(city_name, country_name, max_results)
        
        added = 0
        for prospect in prospects:
            if self.db.insert_prospect(prospect):
                self.db.update_status(prospect['phone_number'], 'to_contact')
                added += 1
        
        self.log("="*60)
        self.log(f"✅ TERMINÉ")
        self.log(f"📊 Trouvés: {len(prospects)}")
        self.log(f"📊 Ajoutés: {added}")
        self.log(f"📊 API calls: {self.api_calls}")
        self.log("="*60)
        
        return added

if __name__ == "__main__":
    scraper = UniversalScraper()
    
    if len(sys.argv) >= 2:
        city = sys.argv[1]
        country = sys.argv[2] if len(sys.argv) >= 3 else None
        max_res = int(sys.argv[3]) if len(sys.argv) >= 4 else 20
        
        scraper.run(city, country, max_res)
    else:
        print("Usage: python3 google_places_scraper.py <ville> [pays] [max_results]")
        print("Exemples:")
        print("  python3 google_places_scraper.py Tokyo Japan 15")
        print("  python3 google_places_scraper.py Bangkok Thailand 20")
        print("  python3 google_places_scraper.py 'Mexico DF' Mexico 10")
```

---

**Instructions pour Anna:**
```
Pour chercher N'IMPORTE où dans le monde:

python3 ~/.openclaw/workspace/scripts/google_places_scraper.py "Tokyo" "Japan" 15
python3 ~/.openclaw/workspace/scripts/google_places_scraper.py "Bangkok" "Thailand" 20
python3 ~/.openclaw/workspace/scripts/google_places_scraper.py "Marrakech" "Morocco" 10
python3 ~/.openclaw/workspace/scripts/google_places_scraper.py "Dubai" "UAE" 15

Le script détecte automatiquement les codes pays et normalise les téléphones.
