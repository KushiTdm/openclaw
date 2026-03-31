#!/usr/bin/env python3
"""
Google Places Scraper — Anna / NeuraWeb
Cherche des entreprises sans site web en Colombie et les ajoute dans Airtable.
Usage: python3 google_places_scraper.py "Bogotá" "Colombia" 20
"""

import googlemaps
import json
import time
import sys
from datetime import datetime
from pathlib import Path

CREDENTIALS_PATH = Path.home() / ".openclaw/credentials/google_places.json"
AIRTABLE_CREDENTIALS = Path.home() / ".openclaw/credentials/airtable.json"


def load_google_key():
    if CREDENTIALS_PATH.exists():
        with open(CREDENTIALS_PATH) as f:
            return json.load(f).get("api_key")
    print("❌ Credentials Google Places non trouvés")
    return None


def load_airtable():
    """Charge les credentials Airtable et retourne l'objet table."""
    if not AIRTABLE_CREDENTIALS.exists():
        print("❌ Credentials Airtable non trouvés")
        return None
    with open(AIRTABLE_CREDENTIALS) as f:
        creds = json.load(f)
    try:
        from pyairtable import Api
        api = Api(creds["api_key"])
        return api.table(creds["base_id"], "Prospects")
    except Exception as e:
        print(f"❌ Erreur connexion Airtable: {e}")
        return None


def get_existing_phones(table):
    """Récupère tous les téléphones déjà dans Airtable pour éviter les doublons."""
    try:
        records = table.all(fields=["Phone"])
        return {r["fields"].get("Phone", "").replace(" ", "") for r in records if "Phone" in r["fields"]}
    except Exception as e:
        print(f"⚠️ Impossible de récupérer les doublons: {e}")
        return set()


def normalize_phone(phone):
    """Normalise un numéro de téléphone colombien."""
    phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace(".", "")
    if phone.startswith("+"):
        return phone
    if phone.startswith("57"):
        return "+" + phone
    if phone.startswith("0"):
        phone = phone[1:]
    return "+57" + phone


def detect_type(name):
    name_lower = name.lower()
    if any(w in name_lower for w in ["restaurante", "restaurant", "comida", "cocina", "pizza", "burger", "café", "cafetería"]):
        return "restaurant"
    if any(w in name_lower for w in ["hotel", "hostal", "hostel", "alojamiento", "hospedaje"]):
        return "hotel"
    if any(w in name_lower for w in ["salón", "peluquería", "barbería", "spa", "estética", "belleza"]):
        return "salon"
    if any(w in name_lower for w in ["clínica", "médico", "dental", "consultorio", "farmacia"]):
        return "health"
    if any(w in name_lower for w in ["tienda", "almacén", "boutique", "ropa", "moda"]):
        return "retail"
    return "business"


def search_city(city_name, country_name, max_results=20):
    api_key = load_google_key()
    if not api_key:
        return

    table = load_airtable()
    if not table:
        return

    gmaps = googlemaps.Client(key=api_key)
    existing_phones = get_existing_phones(table)

    print(f"\n{'='*60}")
    print(f"🔍 Recherche: {city_name}, {country_name}")
    print(f"{'='*60}")

    stats = {"found": 0, "without_website": 0, "added": 0, "duplicates": 0, "skipped_has_website": 0}
    api_calls = 0

    # Plusieurs types de recherche pour maximiser les résultats
    search_queries = [
        f"negocios {city_name} {country_name}",
        f"restaurantes {city_name} {country_name}",
        f"hoteles {city_name} {country_name}",
        f"tiendas {city_name} {country_name}",
        f"servicios {city_name} {country_name}",
    ]

    seen_place_ids = set()
    all_prospects = []

    for query in search_queries:
        if len(all_prospects) >= max_results * 2:
            break
        try:
            results = gmaps.places(query=query, language="es")
            api_calls += 1
            for place in results.get("results", []):
                if place["place_id"] not in seen_place_ids:
                    seen_place_ids.add(place["place_id"])
                    all_prospects.append(place)
        except Exception as e:
            print(f"⚠️ Erreur recherche '{query}': {e}")
        time.sleep(0.5)

    print(f"📊 {len(all_prospects)} établissements trouvés au total")

    added = 0
    for place in all_prospects:
        if added >= max_results:
            break

        place_id = place.get("place_id")
        try:
            details = gmaps.place(
                place_id,
                fields=["name", "international_phone_number", "formatted_phone_number",
                        "website", "formatted_address", "rating", "user_ratings_total",
                        "business_status"]
            )
            api_calls += 1
            result = details.get("result", {})

            # Ignorer si fermé définitivement
            if result.get("business_status") == "CLOSED_PERMANENTLY":
                continue

            phone_raw = result.get("international_phone_number") or result.get("formatted_phone_number")
            if not phone_raw:
                continue

            website = result.get("website", "")
            stats["found"] += 1

            # Ignorer si a déjà un site web
            if website:
                stats["skipped_has_website"] += 1
                continue

            stats["without_website"] += 1
            phone = normalize_phone(phone_raw)

            # Vérifier doublon
            if phone in existing_phones:
                print(f"  ⚠️ Doublon: {result.get('name')} ({phone})")
                stats["duplicates"] += 1
                continue

            # Ajouter dans Airtable
            record = {
                "Name": result.get("name", ""),
                "Phone": phone,
                "City": city_name,
                "Type": detect_type(result.get("name", "")),
                "Status": "to_contact",
                "Notes": f"Trouvé via Google Maps le {datetime.now().strftime('%Y-%m-%d')}. Adresse: {result.get('formatted_address', '')}",
            }

            table.create(record)
            existing_phones.add(phone)
            stats["added"] += 1
            added += 1
            print(f"  ✅ Ajouté: {result.get('name')} ({phone})")

        except Exception as e:
            print(f"  ❌ Erreur pour {place.get('name', '?')}: {e}")

        time.sleep(0.3)

    print(f"\n{'='*60}")
    print(f"✅ TERMINÉ — {city_name}")
    print(f"   Trouvés total: {stats['found']}")
    print(f"   Avec site web (ignorés): {stats['skipped_has_website']}")
    print(f"   Sans site web: {stats['without_website']}")
    print(f"   Doublons évités: {stats['duplicates']}")
    print(f"   Ajoutés Airtable: {stats['added']}")
    print(f"   API calls: {api_calls}")
    print(f"{'='*60}\n")

    return stats


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        city = sys.argv[1]
        country = sys.argv[2] if len(sys.argv) >= 3 else "Colombia"
        max_res = int(sys.argv[3]) if len(sys.argv) >= 4 else 20
        search_city(city, country, max_res)
    else:
        print("Usage: python3 google_places_scraper.py <ville> [pays] [max_resultats]")
        print("Ex:    python3 google_places_scraper.py Bogotá Colombia 20")