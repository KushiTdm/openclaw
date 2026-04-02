#!/usr/bin/env python3
"""
weekly_report.py — Rapport hebdomadaire + Auto-amélioration d'Anna
Analyse les performances de la semaine et génère des recommandations via Gemini.

Usage:
  python3 weekly_report.py              # Rapport de la semaine passée
  python3 weekly_report.py --days 14    # Analyse sur 2 semaines
  python3 weekly_report.py --dry-run    # Affiche sans envoyer à Nacer

Déclencher chaque dimanche soir via cron ou HEARTBEAT.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

AIRTABLE_CREDS  = Path.home() / ".openclaw/credentials/airtable.json"
GEMINI_CREDS    = Path.home() / ".openclaw/credentials/gemini.json"
NACER_WHATSAPP  = "+33749775654"


# ── Airtable ──────────────────────────────────────────────────────────────────

def load_airtable():
    if not AIRTABLE_CREDS.exists():
        print("❌ Credentials Airtable manquants")
        sys.exit(1)
    with open(AIRTABLE_CREDS) as f:
        creds = json.load(f)
    from pyairtable import Api
    api = Api(creds["api_key"])
    return api.table(creds["base_id"], "Prospects")


def fetch_week_data(table, days=7):
    """Récupère les interactions de la dernière semaine."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        records = table.all(formula=f"IS_AFTER({{contacted_at}}, '{cutoff}')")
        print(f"✅ {len(records)} interactions récupérées (derniers {days} jours)")
        return records
    except Exception as e:
        print(f"❌ Erreur Airtable: {e}")
        return []


def compute_kpis(records):
    """Calcule les KPIs à partir des records Airtable."""
    total = len(records)
    if total == 0:
        return {}

    by_status   = {}
    by_country  = {}
    by_template = {}
    by_msg_type = {}
    by_lang     = {}
    objections  = {}
    price_disc  = 0

    for r in records:
        f = r.get("fields", {})

        # Statut
        s = f.get("Status", "unknown")
        by_status[s] = by_status.get(s, 0) + 1

        # Pays
        c = f.get("Country", "unknown")
        by_country[c] = by_country.get(c, 0) + 1

        # Template
        t = f.get("Template_used", "unknown")
        by_template[t] = by_template.get(t, 0) + 1

        # Type de message
        mt = f.get("Message_type", "unknown")
        by_msg_type[mt] = by_msg_type.get(mt, 0) + 1

        # Langue
        lg = f.get("Language", "unknown")
        by_lang[lg] = by_lang.get(lg, 0) + 1

        # Objections
        obj = f.get("Objection", "")
        if obj:
            objections[obj] = objections.get(obj, 0) + 1

        # Prix discuté
        if f.get("Price_discussed"):
            price_disc += 1

    replied = sum(v for k, v in by_status.items()
                  if k in ("interested", "qualified", "refused", "client", "no_response")
                  and k != "contacted")

    interested = by_status.get("interested", 0) + by_status.get("qualified", 0)
    clients    = by_status.get("client", 0)

    return {
        "total":        total,
        "replied":      replied,
        "interested":   interested,
        "clients":      clients,
        "price_discussed": price_disc,
        "response_rate":   round(replied / total * 100, 1) if total else 0,
        "interest_rate":   round(interested / total * 100, 1) if total else 0,
        "close_rate":      round(clients / total * 100, 1) if total else 0,
        "by_status":    dict(sorted(by_status.items(), key=lambda x: -x[1])),
        "by_country":   dict(sorted(by_country.items(), key=lambda x: -x[1])[:8]),
        "by_template":  dict(sorted(by_template.items(), key=lambda x: -x[1])),
        "by_msg_type":  by_msg_type,
        "by_language":  dict(sorted(by_lang.items(), key=lambda x: -x[1])),
        "objections":   dict(sorted(objections.items(), key=lambda x: -x[1])),
    }


# ── Gemini ────────────────────────────────────────────────────────────────────

def load_gemini_key():
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    if GEMINI_CREDS.exists():
        with open(GEMINI_CREDS) as f:
            return json.load(f).get("api_key")
    print("❌ GEMINI_API_KEY non trouvée")
    sys.exit(1)


def generate_analysis(kpis: dict, raw_notes: list[str]) -> str:
    """Envoie les KPIs à Gemini et récupère les recommandations."""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("❌ google-genai non installé. Lancer: pip install google-genai --break-system-packages")
        sys.exit(1)

    api_key = load_gemini_key()
    client = genai.Client(api_key=api_key)

    sample_notes = "\n".join(raw_notes[:30]) if raw_notes else "(aucune note disponible)"

    prompt = f"""Tu es un expert en sales et growth pour une agence web B2B qui prospecte des PME via WhatsApp.

Voici les KPIs de la semaine d'Anna, agente commerciale NeuraWeb :

{json.dumps(kpis, ensure_ascii=False, indent=2)}

Exemples de notes de conversation (30 premières) :
{sample_notes}

Génère un rapport d'analyse en FRANÇAIS comprenant :

1. **Résumé performances** (2-3 phrases synthétiques)
2. **Points forts de la semaine** (ce qui a bien marché)
3. **Points faibles** (ce qui n'a pas marché et pourquoi)
4. **Top 3 objections marché** avec explication possible
5. **3 à 5 recommandations concrètes et actionnables** pour la semaine suivante
   - Format : ACTION PRÉCISE → résultat attendu
   - Exemples : "Tester un message vocal après 24h sans réponse en Colombie",
     "Éviter le créneau 17h-18h en Inde (faible taux de réponse)"
6. **2 nouveaux scripts à tester** (1 texte + 1 vocal 15-20 secondes)
   - Adaptés aux marchés les plus actifs

Sois concis, percutant, actionnable. Pas de jargon. Le rapport sera lu par le CEO."""

    resp = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
    )
    return resp.text


# ── Rapport ───────────────────────────────────────────────────────────────────

def build_report(kpis: dict, analysis: str, days: int) -> str:
    """Construit le message WhatsApp final."""
    now  = datetime.now()
    week_end   = now.strftime("%d/%m")
    week_start = (now - timedelta(days=days)).strftime("%d/%m")

    top_countries = list(kpis.get("by_country", {}).items())[:3]
    country_lines = "\n".join(
        f"  • {c}: {n} contacts" for c, n in top_countries
    ) or "  (aucune donnée)"

    top_templates = list(kpis.get("by_template", {}).items())[:3]
    template_lines = "\n".join(
        f"  • Template {t}: {n} envois" for t, n in top_templates
    ) or "  (aucune donnée)"

    text_count  = kpis.get("by_msg_type", {}).get("text", 0)
    voice_count = kpis.get("by_msg_type", {}).get("voice", 0)

    report = f"""📊 Rapport Anna — {week_start} au {week_end}

PERFORMANCE :
• Messages envoyés : {kpis.get('total', 0)} (texte: {text_count} | vocal: {voice_count})
• Taux de réponse : {kpis.get('response_rate', 0)}%
• Taux d'intérêt : {kpis.get('interest_rate', 0)}%
• Clients closés : {kpis.get('clients', 0)}
• Prix discutés : {kpis.get('price_discussed', 0)}

TOP PAYS :
{country_lines}

TOP TEMPLATES :
{template_lines}

ANALYSE & RECOMMANDATIONS :
{analysis}
"""
    return report.strip()


# ── Envoi WhatsApp ─────────────────────────────────────────────────────────────

def send_whatsapp(message: str):
    """Envoie le rapport à Nacer via OpenClaw."""
    import subprocess
    import tempfile

    # Écrire dans un fichier temporaire (messages longs)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(message)
        tmp_path = f.name

    # Envoyer via openclaw (texte)
    result = subprocess.run(
        ["npx", "openclaw", "message", "send",
         "--channel", "whatsapp",
         "--target", NACER_WHATSAPP,
         "--text", message[:4000]],  # WhatsApp limit
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"✅ Rapport envoyé à Nacer ({NACER_WHATSAPP})")
    else:
        print(f"❌ Erreur envoi: {result.stderr}")

    os.unlink(tmp_path)


# ── Sauvegarde locale ─────────────────────────────────────────────────────────

def save_report(report: str, kpis: dict):
    """Sauvegarde le rapport et les KPIs localement."""
    today = datetime.now().strftime("%Y-%m-%d")
    report_dir = Path.home() / ".openclaw/workspace/reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    report_path = report_dir / f"weekly_{today}.md"
    report_path.write_text(report, encoding='utf-8')

    kpis_path = report_dir / f"kpis_{today}.json"
    kpis_path.write_text(json.dumps(kpis, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f"✅ Rapport sauvegardé : {report_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    days    = 7
    dry_run = "--dry-run" in sys.argv

    for i, arg in enumerate(sys.argv):
        if arg == "--days" and i + 1 < len(sys.argv):
            days = int(sys.argv[i + 1])

    print(f"\n📊 Rapport hebdomadaire Anna — {days} derniers jours")
    print("=" * 60)

    # 1. Charger les données
    table   = load_airtable()
    records = fetch_week_data(table, days)

    if not records:
        print("⚠️ Aucune donnée disponible pour cette période.")
        return

    # 2. Calculer les KPIs
    kpis = compute_kpis(records)
    print(f"\n📈 KPIs calculés : {kpis.get('total')} contacts, "
          f"{kpis.get('response_rate')}% réponse, "
          f"{kpis.get('clients')} clients")

    # 3. Extraire les notes de conversation
    notes = [
        r["fields"].get("Notes", "")
        for r in records if r["fields"].get("Notes")
    ]

    # 4. Analyse Gemini
    print("\n🤖 Génération de l'analyse via Gemini...")
    analysis = generate_analysis(kpis, notes)

    # 5. Construire le rapport
    report = build_report(kpis, analysis, days)
    print("\n" + "=" * 60)
    print(report)
    print("=" * 60)

    # 6. Sauvegarder
    save_report(report, kpis)

    # 7. Envoyer à Nacer
    if not dry_run:
        print("\n📱 Envoi à Nacer...")
        send_whatsapp(report)
    else:
        print("\n⚠️ Mode dry-run — rapport non envoyé.")


if __name__ == "__main__":
    main()