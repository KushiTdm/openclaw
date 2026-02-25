#!/usr/bin/env python3
"""
Google Places Scraper v4 - UNIVERSEL avec dissociation SITE WEB / SANS SITE WEB
- Hotels AVEC site web → DB avec flag has_website=True
- Hotels SANS site web → DB avec flag has_website=False
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
        self.api_key = self._load_google_key()
        self.gmaps = googlemaps.Client(key=self.api_key) if self.api_key else None
        self.brave_key = self._load_brave_key()
        self.api_calls = 0
        self.stats = {
            'found': 0,
            'with_website': 0,
            'without_website': 0,
            'added': 0,
            'duplicates': 0
        }

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
        if not self.brave_key:
            return self._get_default_code(country_name)
        try:
            query = f"{country_name} country calling code phone"
            headers = {'Accept': 'application/json', 'X-Subscription-Token': self.brave_key}
            params = {'q': query, 'count': 3}
            response = requests.get(
                'https://api.search.brave.com/res/v1/web/search',
                headers=headers, params=params, timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                for result in data.get('web', {}).get('results', []):
                    text = result.get('description', '') + result.get('title', '')
                    import re
                    matches = re.findall(r'\+\d{1,4}', text)
                    if matches:
                        return matches[0]
            return self._get_default_code(country_name)
        except Exception:
            return self._get_default_code(country_name)

    def _get_default_code(self, country_name):
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
        return '+1'

    def detect_country_from_address(self, address):
        parts = address.split(',')
        if len(parts) >= 2:
            potential_country = parts[-1].strip()
            import re
            potential_country = re.sub(r'\d+', '', potential_country).strip()
            if len(potential_country) > 2:
                return potential_country
        return 'Unknown'

    def normalize_phone_universal(self, phone, country_name):
        phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('.', '')
        if phone.startswith('+'):
            return phone
        country_code = self.get_country_code_universal(country_name)
        phone = phone.lstrip('0')
        return country_code + phone

    def _detect_type(self, name):
        name_lower = name.lower()
        if any(w in name_lower for w in ['hostel', 'hostal', 'backpack', 'dormitory']):
            return 'hostel'
        elif any(w in name_lower for w in ['lodge', 'resort', 'villa']):
            return 'lodge'
        elif any(w in name_lower for w in ['tour', 'travel', 'agency', 'agencia']):
            return 'tour_operator'
        return 'hotel'

    def search_city_universal(self, city_name, country_name=None, max_results=20):
        """
        Recherche UNIVERSELLE — sépare hotels AVEC et SANS site web
        Returns: (with_website_list, without_website_list)
        """
        if not self.gmaps:
            self.log("❌ Google Maps API non configurée")
            return [], []

        location_query = f"{city_name}, {country_name}" if country_name else city_name
        self.log(f"🔍 Recherche à {location_query}")

        with_website = []
        without_website = []

        try:
            query = f"hotel hostel accommodation {location_query}"
            results = self.gmaps.places(query=query, language='en')
            self.api_calls += 1
            places = results.get('results', [])
            self.log(f"📊 {len(places)} établissements trouvés sur Google Places")

            for place in places[:max_results]:
                place_id = place.get('place_id')
                details = self.gmaps.place(
                    place_id,
                    fields=['name', 'international_phone_number', 'formatted_phone_number',
                            'website', 'formatted_address', 'rating', 'user_ratings_total']
                )
                self.api_calls += 1
                result = details.get('result', {})

                phone = result.get('international_phone_number') or result.get('formatted_phone_number')
                if not phone:
                    continue

                address = result.get('formatted_address', '')
                detected_country = country_name or self.detect_country_from_address(address)
                phone = self.normalize_phone_universal(phone, detected_country)
                website = result.get('website', '')

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
                    'review_count': result.get('user_ratings_total'),
                    'website': website,
                    'has_website': bool(website)
                }

                self.stats['found'] += 1

                if website:
                    with_website.append(prospect)
                    self.stats['with_website'] += 1
                    self.log(f"  🌐 AVEC site: {prospect['name']} → {website}")
                else:
                    without_website.append(prospect)
                    self.stats['without_website'] += 1
                    self.log(f"  📵 SANS site: {prospect['name']}")

                time.sleep(0.5)

        except Exception as e:
            self.log(f"❌ Erreur recherche {location_query}: {e}")
            self.db.log_error('google_places_search', str(e), location_query)

        self.log(f"✅ Avec site web: {len(with_website)} | Sans site web: {len(without_website)}")
        return with_website, without_website

    def run(self, city_name, country_name=None, max_results=20):
        """Point d'entrée principal"""
        self.log("=" * 60)
        self.log(f"🚀 SCRAPING: {city_name}" + (f", {country_name}" if country_name else ""))
        self.log("=" * 60)

        with_website, without_website = self.search_city_universal(city_name, country_name, max_results)

        added_with = 0
        added_without = 0

        # Ajouter les hotels AVEC site web
        for prospect in with_website:
            if self.db.insert_prospect(prospect):
                self.db.update_status(prospect['phone_number'], 'to_contact')
                added_with += 1

        # Ajouter les hotels SANS site web
        for prospect in without_website:
            if self.db.insert_prospect(prospect):
                self.db.update_status(prospect['phone_number'], 'to_contact')
                added_without += 1

        self.stats['added'] = added_with + added_without

        self.log("=" * 60)
        self.log(f"✅ TERMINÉ — {city_name}")
        self.log(f"   🌐 Avec site web:  trouvés={len(with_website)}, ajoutés={added_with}")
        self.log(f"   📵 Sans site web:  trouvés={len(without_website)}, ajoutés={added_without}")
        self.log(f"   📊 Total ajoutés: {self.stats['added']}")
        self.log(f"   🔁 API calls: {self.api_calls}")
        self.log("=" * 60)

        return self.stats


if __name__ == "__main__":
    scraper = UniversalScraper()
    if len(sys.argv) >= 2:
        city = sys.argv[1]
        country = sys.argv[2] if len(sys.argv) >= 3 else None
        max_res = int(sys.argv[3]) if len(sys.argv) >= 4 else 20
        scraper.run(city, country, max_res)
    else:
        print("Usage: python3 google_places_scraper.py <ville> [pays] [max_results]")
        print("Ex:    python3 google_places_scraper.py Quito Ecuador 20")