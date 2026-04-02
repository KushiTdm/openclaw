#!/usr/bin/env python3
"""
Timezone Selector — Anna / NeuraWeb Global
Détermine quels pays sont dans la fenêtre de contact (9h–18h heure locale).
Exclut la France.

Usage:
  python3 timezone_selector.py              # Liste les pays actifs maintenant
  python3 timezone_selector.py --best       # Recommande les 3 meilleures cibles
  python3 timezone_selector.py --json       # Sortie JSON pour scripts
"""

import datetime
import json
import sys

# Format : (offset_utc, pays, langue_iso, marché, priorité_1-3)
# priorité 1 = haute (ROI fort), 2 = moyenne, 3 = basse
# marché : "emerging" | "medium" | "premium"
COUNTRY_MAP = [
    (-8,   "USA Pacifique",         "en", "premium",  2),
    (-7,   "USA Montagne",          "en", "premium",  2),
    (-7,   "Mexique (nord-ouest)",  "es", "medium",   1),
    (-6,   "Mexique",               "es", "medium",   1),
    (-6,   "Guatemala",             "es", "emerging", 1),
    (-6,   "Salvador",              "es", "emerging", 1),
    (-6,   "Honduras",              "es", "emerging", 1),
    (-5,   "Colombie",              "es", "emerging", 1),
    (-5,   "Pérou",                 "es", "emerging", 1),
    (-5,   "Équateur",              "es", "emerging", 1),
    (-5,   "USA Est",               "en", "premium",  2),
    (-5,   "Cuba",                  "es", "emerging", 2),
    (-4,   "Chili",                 "es", "emerging", 1),
    (-4,   "Venezuela",             "es", "emerging", 2),
    (-4,   "Bolivie",               "es", "emerging", 2),
    (-4,   "Paraguay",              "es", "emerging", 2),
    (-3,   "Argentine",             "es", "emerging", 1),
    (-3,   "Brésil Est",            "pt", "emerging", 1),
    (-3,   "Uruguay",               "es", "emerging", 2),
    (-2,   "Brésil Centre",         "pt", "emerging", 1),
    ( 0,   "UK",                    "en", "premium",  2),
    ( 0,   "Irlande",               "en", "premium",  3),
    ( 0,   "Portugal",              "pt", "medium",   2),
    ( 0,   "Sénégal",               "fr", "emerging", 1),
    ( 0,   "Ghana",                 "en", "emerging", 1),
    ( 0,   "Côte d'Ivoire",         "fr", "emerging", 1),
    ( 0,   "Guinée",                "fr", "emerging", 2),
    ( 1,   "Espagne",               "es", "medium",   1),
    ( 1,   "Allemagne",             "de", "premium",  2),
    ( 1,   "Italie",                "it", "medium",   2),
    ( 1,   "Belgique",              "fr", "medium",   2),
    ( 1,   "Suisse",                "fr", "medium",   2),
    ( 1,   "Pays-Bas",              "en", "medium",   2),
    ( 1,   "Maroc",                 "ar", "emerging", 1),
    ( 1,   "Algérie",               "ar", "emerging", 1),
    ( 1,   "Tunisie",               "ar", "emerging", 1),
    ( 1,   "Nigeria",               "en", "emerging", 1),
    ( 1,   "Cameroun",              "fr", "emerging", 1),
    ( 1,   "Sénégal (hiv.)",        "fr", "emerging", 1),
    ( 2,   "Égypte",                "ar", "emerging", 1),
    ( 2,   "Afrique du Sud",        "en", "medium",   1),
    ( 2,   "Kenya",                 "en", "emerging", 1),
    ( 2,   "Jordanie",              "ar", "emerging", 2),
    ( 2,   "Liban",                 "ar", "emerging", 2),
    ( 2,   "Tanzanie",              "en", "emerging", 2),
    ( 2,   "Mozambique",            "pt", "emerging", 2),
    ( 3,   "Arabie Saoudite",       "ar", "premium",  1),
    ( 3,   "Kuwait",                "ar", "premium",  2),
    ( 3,   "Turquie",               "en", "medium",   2),
    ( 3,   "Éthiopie",              "en", "emerging", 2),
    ( 4,   "EAU",                   "ar", "premium",  1),
    ( 4,   "Qatar",                 "ar", "premium",  1),
    ( 4,   "Bahreïn",               "ar", "premium",  2),
    ( 4,   "Oman",                  "ar", "premium",  2),
    ( 4.5, "Afghanistan",           "en", "emerging", 3),
    ( 5,   "Pakistan",              "en", "emerging", 2),
    ( 5.5, "Inde",                  "en", "emerging", 1),
    ( 5.75,"Népal",                 "en", "emerging", 3),
    ( 6,   "Bangladesh",            "en", "emerging", 2),
    ( 6,   "Sri Lanka",             "en", "emerging", 2),
    ( 7,   "Thaïlande",             "en", "medium",   1),
    ( 7,   "Vietnam",               "en", "medium",   1),
    ( 7,   "Indonésie Ouest",       "en", "medium",   1),
    ( 7,   "Cambodge",              "en", "emerging", 2),
    ( 8,   "Philippines",           "en", "emerging", 1),
    ( 8,   "Malaisie",              "en", "medium",   1),
    ( 8,   "Singapour",             "en", "premium",  2),
    ( 8,   "Hong Kong",             "en", "premium",  2),
    ( 8,   "Taïwan",                "en", "medium",   2),
    ( 8,   "Chine",                 "en", "medium",   3),
    ( 8,   "Indonésie Est",         "en", "medium",   1),
    ( 9,   "Japon",                 "ja", "premium",  3),
    ( 9,   "Corée du Sud",          "ko", "premium",  3),
    (10,   "Australie Est",         "en", "premium",  2),
    (10,   "Papouasie-NG",          "en", "emerging", 3),
    (11,   "Australie AEDT",        "en", "premium",  3),
    (12,   "Nouvelle-Zélande",      "en", "premium",  3),
]

# Pays absolument exclus
EXCLUDED = ["France"]
WINDOW_START = 9
WINDOW_END   = 18


def get_active_countries(start=WINDOW_START, end=WINDOW_END):
    """Retourne les pays dans la fenêtre de contact à l'heure actuelle."""
    now = datetime.datetime.utcnow()
    utc_h = now.hour + now.minute / 60

    active = []
    for (offset, country, lang, market, priority) in COUNTRY_MAP:
        if country in EXCLUDED:
            continue
        local_h = (utc_h + offset) % 24
        if start <= local_h < end:
            active.append({
                "offset": offset,
                "country": country,
                "language": lang,
                "market": market,
                "priority": priority,
                "local_time": f"{int(local_h):02d}:{int((local_h % 1) * 60):02d}",
            })

    # Tri : priorité d'abord, puis marchés émergents (meilleur ROI NeuraWeb)
    market_order = {"emerging": 0, "medium": 1, "premium": 2}
    active.sort(key=lambda x: (x["priority"], market_order[x["market"]]))
    return active


def recommend_targets(n=3):
    """Retourne les N meilleures cibles pour maintenant."""
    active = get_active_countries()
    # Priorité 1 en premier
    p1 = [c for c in active if c["priority"] == 1]
    return (p1 if p1 else active)[:n]


def main():
    now = datetime.datetime.utcnow()
    json_mode = "--json" in sys.argv
    best_mode = "--best" in sys.argv

    if json_mode:
        targets = recommend_targets(3)
        print(json.dumps(targets, ensure_ascii=False, indent=2))
        return

    print(f"\n🕐 UTC : {now.strftime('%H:%M')}  ({now.strftime('%A %d %B')})")
    print("=" * 62)

    active = get_active_countries()

    if not active:
        print("😴 Aucun pays dans la fenêtre 9h–18h actuellement.")
        print("   → Anna peut chercher des prospects offline (scraping, DB).")
        print("   → Prochaine fenêtre dans quelques heures.")
        return

    if best_mode:
        targets = recommend_targets(3)
        print(f"🎯 CIBLES RECOMMANDÉES MAINTENANT :\n")
        for i, t in enumerate(targets, 1):
            print(f"  {i}. {t['country']:<28} {t['local_time']} locale | {t['language'].upper()}")
        return

    print(f"✅ {len(active)} pays dans la fenêtre de contact :\n")
    priority_icons = {1: "🔥", 2: "⭐", 3: "💡"}
    last_priority = None
    for c in active:
        if c["priority"] != last_priority:
            labels = {1: "Priorité haute (ROI fort)", 2: "Priorité moyenne", 3: "Priorité basse"}
            print(f"\n  {labels[c['priority']]} :")
            last_priority = c["priority"]
        icon = priority_icons[c["priority"]]
        print(f"    {icon} {c['country']:<28} {c['local_time']} locale | {c['language'].upper()} | {c['market']}")

    print(f"\n{'=' * 62}")
    targets = recommend_targets(3)
    print(f"🎯 CIBLES RECOMMANDÉES (top 3) :")
    for i, t in enumerate(targets, 1):
        print(f"  {i}. {t['country']} ({t['local_time']} locale, langue: {t['language'].upper()})")
    print()


if __name__ == "__main__":
    main()