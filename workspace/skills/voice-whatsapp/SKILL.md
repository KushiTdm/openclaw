---
name: voice-whatsapp
description: Envoie un message vocal sur WhatsApp via Gemini TTS (Google AI Studio). Utilise ce skill à chaque fois que tu dois répondre par la voix, quand on te demande un vocal, ou pour tout message important.
---

# Voice WhatsApp — Anna (Gemini TTS)

Remplacement ElevenLabs → Gemini 2.5 Flash TTS (Google AI Studio, crédits gratuits).

## Prérequis (une seule fois)

```bash
pip install google-genai --break-system-packages
export GEMINI_API_KEY="ta_clé_aistudio"
# Ou sauvegarder dans : ~/.openclaw/credentials/gemini.json → {"api_key": "..."}
```

## Workflow complet — À suivre exactement

### Étape 1 — Générer l'audio via Gemini TTS
```bash
python3 ~/workspace/scripts/gemini_tts.py "TEXTE_ICI" /tmp/anna_voice.ogg
```

> Le script génère directement un OGG Opus prêt pour WhatsApp (WAV → OGG Opus via ffmpeg).
> Voix par défaut : **Zephyr** (chaleureuse). Ajouter `--voice NomVoix` pour changer.

### Étape 2 — Envoyer sur WhatsApp
```bash
npx openclaw message send --channel whatsapp --target "NUMERO_DESTINATAIRE" --media "/tmp/anna_voice.ogg"
```

### Étape 3 — Répondre NO_REPLY
Après envoi du vocal, ta réponse textuelle doit être uniquement :
NO_REPLY

## Voix disponibles

| Voix | Style | Recommandé pour |
|------|-------|-----------------|
| Zephyr | Chaleureuse | ✅ Anna par défaut |
| Aoede | Légère | Espagnol décontracté |
| Leda | Jeune | Prospectos jeunes |
| Achird | Amicale | Conversations casual |
| Sulafat | Chaleureuse | Alternative à Zephyr |
| Schedar | Neutre | Rapports à Nacer |
| Sadaltager | Experte | Contenu professionnel |

## Exemples

```bash
# Message en espagnol pour un prospecto
python3 ~/workspace/scripts/gemini_tts.py \
  "Hola, soy Anna de NeuraWeb. ¿Tiene un momento?" \
  /tmp/anna_voice.ogg

# Message en français pour Nacer
python3 ~/workspace/scripts/gemini_tts.py \
  "Nacer, j'ai un prospect intéressé à Bogotá." \
  /tmp/anna_voice.ogg --voice Schedar

# Puis envoyer
npx openclaw message send --channel whatsapp --target "+33749775654" --media "/tmp/anna_voice.ogg"
```

## Règles absolues
- TOUJOURS OGG Opus (le script s'en charge automatiquement)
- JAMAIS utiliser [[tts:...]] directives
- JAMAIS utiliser MEDIA: token (bug #54131 toujours actif)
- Le NUMERO_DESTINATAIRE = numéro de la personne qui t'a écrit (format +33... ou +57...)
- Nacer = +33749775654