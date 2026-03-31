# HEARTBEAT.md

## Checks périodiques

1. **Airtable** — Y a-t-il des prospectos avec `status = to_contact` à contacter ?
   - Si oui et que Nacer n'a pas dit d'attendre → contacter (vérifier timing humain)
   
2. **Réponses** — Y a-t-il des réponses de prospectos à traiter ?
   - Si oui → mettre à jour Airtable + notifier Nacer si prospect intéressé

3. **Suivi** — Y a-t-il des prospectos `contacted` depuis +48h sans réponse ?
   - Envisager un message de relance (Template B)

Si rien à faire → répondre `HEARTBEAT_OK`