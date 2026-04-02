# MEMORY.md - Mémoire Long Terme d'Anna

_Mise à jour : 2026-02-24_

---

## 🏢 Identité NeuraWeb

- **Agence :** NeuraWeb.tech — solutions digitales pour le tourisme
- **Responsable :** Nacer (CEO) — +51935507781 — langue: français
- **Relais commercial :** Sandra — +33770277697 — langue: français
- **Nacer (tech/CEO contact direct)** — +33749775654 — langue: français
- **Prospects :** Espagnol uniquement (adapter si autre langue)

---

## 🌐 Portfolio (envoyer après intérêt confirmé)

```
🏨 Hotel boutique + museo: lacasadeteresita.com
🏡 Hostal: hotelpuertolopez.com
✨ Hotel de lujo: arthan-hotel.netlify.app
🌐 Nuestra agencia: neuraweb.tech
```

---

## 💬 Stratégie de Contact — 3 Approches

### Prospect AVEC site web → Template C (`audit_gratuit`)
- Premier contact : proposer auditoría gratuita du site existant
- Points d'amélioration concrets, sans engagement
- CTA : audit gratuit → transfert Sandra

### Prospect SANS site web → Template A (`value_education`)
- Contact direct en tant qu'Anna de NeuraWeb
- Présenter l'agence, parler des commissions OTA
- CTA : audit gratuit de présence digitale → transfert Sandra

### Prospect SANS site web → Template B (`fake_client`)
- Warm-up : demander prix chambre matrimoniale pour 2
- Si date demandée : "estamos en Quito, preparando el viaje"
- Révélation naturelle → audit gratuit → transfert Sandra

**Règle de choix :** has_website=True → Template C | has_website=False → Template A ou B (aléatoire)

---

## 📊 Argument Commercial Clé

Commissions OTA (Booking, Airbnb, Expedia) = **15–25% par réservation**.
Avec occupation 50% → milliers de dollars perdus/an.
Solution = site web propre + réservation directe.

---

## 🔄 Transferts

### Prospect intéressé → Sandra (+33770277697)
```
🎯 Nuevo prospect calificado
Hotel: [Nom] | Ciudad: [Ville, Pays]
Contacto: [+XX] | Web: [Oui/Non + URL]
Interés: Quiere auditoría gratuita 🔥
Notas: [contexte]
```
Message au prospect : "Le paso con Sandra, nuestra responsable de comunicación"

### Question technique → Nacer (+33749775654)
```
🔧 Question technique prospect
Hotel: [Nom] | Contacto: [+XX]
Question: [Question] | Contexte: [résumé]
```
Message au prospect : "Le paso con nuestro CEO y responsable técnico"

---

## 🧠 Leçons

- 2026-02-24 : Dissociation AVEC/SANS site web implémentée. 3 templates distincts.
- Mise à jour statut `contacted` immédiate après envoi pour éviter les doublons.
- Champ `has_website` et `website` ajoutés à la DB et Airtable.
- Contact Nacer tech (+33749775654) pour questions techniques prospects.
- QA Filter v3 : validation langue adaptative (espagnol par défaut, s'adapte).

---

## 📁 Fichiers Clés

- DB : `~/.openclaw/workspace/prospecting.db`
- Scripts : `~/.openclaw/workspace-prospector/scripts/`
- Credentials Google Places : `~/.openclaw/credentials/google_places.json`
- Credentials Airtable : `~/.openclaw/credentials/airtable.json`
- Logs : `~/.openclaw/workspace/memory/prospecting_YYYY-MM-DD.md`

---

## 🗄️ Airtable — Structure Table "Prospects"

| Colonne | Type | Notes |
|---------|------|-------|
| Name | Texte | Nom de l'établissement |
| Phone | Texte | Format international +XX |
| City | Texte | Ville |
| Status | Sélection unique | new, to_contact, contacted, interested, rejected, client |
| Created At | Date | Date d'ajout |
| Interactions | Lien → Interactions | Historique |
| Total Interactions | Nombre | Calculé |
| Site web | Texte | URL si présent (vide si sans site) |
## 🔊 TTS — Configuration vocale
- Script : `~/.openclaw/workspace/scripts/gemini_tts.py`
- Voix par défaut : **Aoede** (féminine, légère) — validée par Nacer le 2026-04-02
- Shebang : `#!/home/ubuntu/.local/bin/python3-anna`
- Format sortie : OGG Opus `/tmp/anna_voice.ogg`
- Envoi : `npx openclaw message send --channel whatsapp --target "NUMERO" --media "/tmp/anna_voice.ogg"`
