#!/bin/bash
echo "🔍 Vérification des credentials..."

# Google Places
if [ -f "/home/ubuntu/.openclaw/credentials/google_places.json" ]; then
    echo "✅ Google Places credentials trouvés"
    cat /home/ubuntu/.openclaw/credentials/google_places.json
else
    echo "❌ Google Places credentials manquants"
fi

# Airtable
if [ -f "/home/ubuntu/.openclaw/credentials/airtable.json" ]; then
    echo "✅ Airtable credentials trouvés"
else
    echo "❌ Airtable credentials manquants"
fi

# Auth profiles
echo ""
echo "📋 Auth Profiles par agent:"
for agent in main prospector salesperson twitter; do
    profile_path="/home/ubuntu/.openclaw/agents/$agent/agent/auth-profiles.json"
    if [ -f "$profile_path" ]; then
        echo "  ✅ $agent"
    else
        echo "  ❌ $agent (manquant)"
    fi
done
