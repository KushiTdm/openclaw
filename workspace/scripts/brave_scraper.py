#!/usr/bin/env python3
"""
Brave Search Scraper — Anna / NeuraWeb
Alternative à Google Places pour trouver des entreprises sans site web.
Usage: python3 brave_scraper.py "Medellín" 20
"""

import requests
import json
import sys
import re
from datetime import datetime
from pathlib import Path

BRAVE_CREDENTIALS = Path.home() / ".openclaw/credentials/brave.json"
AIRTABLE_CREDENTIALS = Path.home() / ".openclaw/credentials/airtable.json"


def load_brave_key():
    if BRAVE_CREDENTIALS.exists():
        with open(BRAVE_CREDENTIALS) as f:
            return json.load(f).get("api_key")
    print("❌ Credentials Brave non trouvés")
    return None


def load_airtable_table():
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
        print(f"❌ Erreur Airtable: {e}")
        return None


def get_existing_phones(table):
    try:
        records = table.all(fields=["Phone"])
        return {r["fields"].get("Phone", "").replace(" ", "") for r in records if "Phone" in r["fields"]}
    except Exception:
        return set()


def brave_search(query, api_key, count=10):
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key
    }
    params = {"q": query, "count": count, "country": "CO", "lang": "es"}
    try:
        response = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers=headers, params=params, timeout=10
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"⚠️ Erreur Brave Search: {e}")
    return {}


def extract_phone_from_text(text):
    """Extrait un numéro de téléphone colombien d'un texte."""
    patterns = [
        r'\+57\s?\d{3}\s?\d{3}\s?\d{4}',
        r'\+57\d{10}',
        r'57\d{10}',
        r'3\d{9}',  # Numéros mobiles colombiens
        r'\(\d{1,3}\)\s?\d{3,4}[\s-]?\d{4}',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            phone = match.group().replace(" ", "").replace("-", "")
            if not phone.startswith("+"):
                if phone.startswith("57"):
                    phone = "+" + phone
                elif phone.startswith("3") and len(phone) == 10:
                    phone = "+57" + phone
            return phone
    return None


def search_city_brave(city_name, max_results=20):
    api_key = load_brave_key()
    if not api_key:
        return

    table = load_airtable_table()
    if not table:
        return

    existing_phones = get_existing_phones(table)

    print(f"\n{'='*60}")
    print(f"🔍 Brave Search: {city_name}, Colombia")
    print(f"{'='*60}")

    queries = [
        f"restaurantes {city_name} Colombia telefono sin pagina web",
        f"hoteles {city_name} Colombia contacto sin web",
        f"tiendas {city_name} Colombia numero telefono",
        f"negocios locales {city_name} Colombia whatsapp",
        f"servicios {city_name} Colombia telefono",
    ]

    added = 0
    stats = {"searched": 0, "added": 0, "duplicates": 0}

    for query in queries:
        if added >= max_results:
            break

        data = brave_search(query, api_key)
        stats["searched"] += 1

        results = data.get("web", {}).get("results", [])
        for result in results:
            if added >= max_results:
                break

            title = result.get("title", "")
            description = result.get("description", "")
            url = result.get("url", "")
            full_text = f"{title} {description}"

            phone = extract_phone_from_text(full_text)
            if not phone:
                continue

            if phone in existing_phones:
                stats["duplicates"] += 1
                continue

            # Créer le record Airtable
            record = {
                "Name": title[:100] if title else "Negocio desconocido",
                "Phone": phone,
                "City": city_name,
                "Type": "business",
                "Status": "to_contact",
                "Notes": f"Trouvé via Brave Search le {datetime.now().strftime('%Y-%m-%d')}. Source: {url[:200]}",
            }

            try:
                table.create(record)
                existing_phones.add(phone)
                stats["added"] += 1
                added += 1
                print(f"  ✅ Ajouté: {title[:50]} ({phone})")
            except Exception as e:
                print(f"  ❌ Erreur insertion: {e}")

    print(f"\n{'='*60}")
    print(f"✅ TERMINÉ Brave Search — {city_name}")
    print(f"   Requêtes: {stats['searched']}")
    print(f"   Doublons évités: {stats['duplicates']}")
    print(f"   Ajoutés Airtable: {stats['added']}")
    print(f"{'='*60}\n")

    return stats


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        city = sys.argv[1]
        max_res = int(sys.argv[2]) if len(sys.argv) >= 3 else 20
        search_city_brave(city, max_res)
    else:
        print("Usage: python3 brave_scraper.py <ville> [max_resultats]")
        print("Ex:    python3 brave_scraper.py Medellín 20")