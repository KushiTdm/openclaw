# QUICK REF - Référence Rapide Anna

## 🔑 Credentials (Vérifier AVANT toute délégation)
```bash
# Google Places API
cat /home/ubuntu/.openclaw/credentials/google_places.json

# Airtable
cat /home/ubuntu/.openclaw/credentials/airtable.json
```

## 🤖 Agents Disponibles

| Agent | ID | Workspace | Usage |
|-------|-----|-----------|-------|
| Prospector | `prospector` | `~/.openclaw/workspace-prospector` | Recherche prospects |
| Salesperson | `salesperson` | `~/.openclaw/workspace-salesperson` | Contact WhatsApp |
| Twitter | `twitter` | `~/.openclaw/workspace-twitter` | Publication tweets |
| QA Filter | `qa_filter` | `~/.openclaw/workspace-qa` | Validation messages |

## 📋 Templates de Commandes

### Prospection
```bash
openclaw agent --agent prospector -m "Cherche 10 prospects à [VILLE], [PAYS]. Exécute google_places_scraper.py, vérifie doublons, ajoute en DB, sync Airtable. Retourne rapport."
```

### Contact prospects
```bash
openclaw agent --agent salesperson -m "Contacte 3 prospects avec status to_contact. Utilise méthode value_education. Valide chaque message via qa_filter. Retourne rapport."
```

### Tweet simple
```bash
openclaw agent --agent twitter -m "Poste un tweet : '[TEXTE]'"
```

### Thread Twitter
```bash
openclaw agent --agent twitter -m "Publie ce thread : [TEXTE_COMPLET]"
```

## 🔍 Auto-Diagnostic en Cas d'Erreur

### Erreur REQUEST_DENIED ou API_KEY_INVALID
1. Vérifier la clé : `cat /home/ubuntu/.openclaw/credentials/google_places.json`
2. Vérifier auth-profiles : `cat /home/ubuntu/.openclaw/agents/prospector/agent/auth-profiles.json`
3. Si clés différentes → Synchroniser
4. Relancer la commande

### Erreur "Either sessionKey or label is required"
→ Tu as utilisé `sessions_send` au lieu de `bash_tool` avec `openclaw agent`
→ TOUJOURS utiliser : `openclaw agent --agent [ID] -m "..."`

### Erreur "agentId is not allowed for sessions_spawn"
→ Tu as utilisé `sessions_spawn` qui est INTERDIT
→ TOUJOURS utiliser : `openclaw agent --agent [ID] -m "..."`
