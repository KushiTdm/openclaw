---
name: voice-whatsapp
description: Envoie un message vocal sur WhatsApp. Utilise ce skill à chaque fois que tu dois répondre par la voix, quand on te demande un vocal, ou pour tout message important. Génère l'audio via ElevenLabs API, convertit en OGG Opus, envoie via openclaw message send --media.
---

# Voice WhatsApp — Anna

Workaround pour le bug OpenClaw #54131 (MEDIA token non délivré sur WhatsApp).
Cette méthode est la SEULE qui fonctionne pour envoyer des vocaux sur WhatsApp.

## Workflow complet — À suivre exactement

### Étape 1 — Générer l'audio ElevenLabs
```bash
curl -s -X POST \
  "https://api.elevenlabs.io/v1/text-to-speech/HRcW1ZTfZR9qe0zq5rIu" \
  -H "xi-api-key: sk_29b1ff7811dc14a169e28d7c2c7c3f53a47ba154602cd581" \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"TEXTE_ICI\",\"model_id\":\"eleven_multilingual_v2\",\"voice_settings\":{\"stability\":0.5,\"similarity_boost\":0.75}}" \
  -o /tmp/anna_voice.mp3
```

### Étape 2 — Convertir en OGG Opus (format WhatsApp obligatoire)
```bash
ffmpeg -y -i /tmp/anna_voice.mp3 -c:a libopus -b:a 64k -ar 48000 -ac 1 -application voip /tmp/anna_voice.ogg
```

### Étape 3 — Envoyer sur WhatsApp
```bash
npx openclaw message send --channel whatsapp --target "NUMERO_DESTINATAIRE" --media "/tmp/anna_voice.ogg"
```

### Étape 4 — Répondre NO_REPLY
Après envoi du vocal, ta réponse textuelle doit être uniquement :
NO_REPLY

## Règles absolues
- TOUJOURS OGG Opus, jamais MP3 direct sur WhatsApp
- JAMAIS utiliser [[tts:...]] directives (passent en texte brut — bug connu)
- JAMAIS utiliser MEDIA: token (ne fonctionne pas sur WhatsApp — bug #54131)
- Le NUMERO_DESTINATAIRE est le numéro de la personne qui t'a écrit (format +33...)
- Remplacer TEXTE_ICI par le message à dire (échapper les guillemets avec \")
- Nacer = +33749775654
