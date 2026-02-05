#!/usr/bin/env python3
"""
Agent Coordinator - Anna Main
Coordonne les interactions entre agents
"""

import subprocess
import json
from pathlib import Path

class AgentCoordinator:
    """Coordination entre agents Anna"""
    
    def __init__(self):
        self.agents = {
            'prospector': 'prospector',
            'salesperson': 'salesperson',
            'qa_filter': 'qa_filter'
        }
    
    def call_agent(self, agent_id, prompt, timeout=120):
        """
        Appelle un agent spécifique via openclaw
        
        Args:
            agent_id: 'prospector', 'salesperson', 'qa_filter'
            prompt: Message à envoyer à l'agent
            timeout: Timeout en secondes
        
        Returns:
            dict: {'success': bool, 'output': str, 'error': str}
        """
        try:
            cmd = [
                'openclaw', 'agent',
                '--agent', agent_id,
                '-m', prompt,
                '--json'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'output': result.stdout,
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'output': None,
                    'error': result.stderr
                }
        
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'output': None,
                'error': f'Timeout après {timeout}s'
            }
        except Exception as e:
            return {
                'success': False,
                'output': None,
                'error': str(e)
            }
    
    def prospect_search(self, city, country, max_results=20):
        """
        Demande au Prospector de chercher des prospects
        """
        prompt = f"""
Cherche des prospects à {city}, {country}.
Max {max_results} résultats.

Exécute:
1. google_places_scraper.py
2. Vérifie doublons
3. Ajoute en DB
4. Sync Airtable

Retourne un rapport structuré.
"""
        return self.call_agent('prospector', prompt)
    
    def contact_prospects(self, limit=5, method=None):
        """
        Demande au Salesperson de contacter des prospects
        AVEC validation QA Filter
        """
        prompt = f"""
Contacte {limit} prospects avec status 'to_contact'.

{"Utilise la méthode: " + method if method else "Méthode au choix selon prospect."}

CRITIQUE: CHAQUE message doit être validé par qa_filter AVANT envoi.

Workflow:
1. Récupère prospects (status=to_contact)
2. Pour chaque prospect:
   a. Prépare message brouillon
   b. Demande validation qa_filter
   c. SI valid=true → Envoie
   d. SI valid=false → Skip + alert Anna
   e. Update DB
3. Rapport final

Retourne:
- Nombre envoyés
- Nombre bloqués par QA
- Erreurs éventuelles
"""
        return self.call_agent('salesperson', prompt)
    
    def validate_message(self, message, recipient, context="initial_contact"):
        """
        Demande au QA Filter de valider un message
        """
        validation_request = {
            'message': message,
            'recipient': recipient,
            'sender': 'salesperson',
            'context': context
        }
        
        prompt = f"""
Valide ce message avant envoi au prospect:

{json.dumps(validation_request, indent=2, ensure_ascii=False)}

Vérifie:
1. Langue (espagnol pour prospect)
2. Pas de mots techniques
3. Pas de messages système
4. Identité correcte (NeuraWeb, pas l'hôtel)
5. Format approprié

Retourne JSON:
{{
  "valid": true/false,
  "reason": "raison si invalid",
  "severity": "critical|warning|info"
}}
"""
        return self.call_agent('qa_filter', prompt, timeout=30)
    
    def get_stats(self):
        """Récupère les stats via Prospector"""
        prompt = """
Exécute db_manager.py pour obtenir les stats.

Retourne:
- Total prospects
- Par status
- Créés aujourd'hui
- Contactés aujourd'hui
"""
        return self.call_agent('prospector', prompt)


def test_coordination():
    """Test de coordination"""
    coord = AgentCoordinator()
    
    print("🧪 TEST COORDINATION MULTI-AGENTS")
    print("=" * 50)
    
    # Test 1: Prospection
    print("\n1️⃣ Test Prospector...")
    result = coord.prospect_search("Cusco", "Peru", 5)
    print(f"   Success: {result['success']}")
    if result['output']:
        print(f"   Output: {result['output'][:200]}...")
    
    # Test 2: Validation QA
    print("\n2️⃣ Test QA Filter...")
    test_message = "Hola, soy Anna de NeuraWeb. ¿Cómo están?"
    result = coord.validate_message(test_message, "+51999999999")
    print(f"   Success: {result['success']}")
    
    # Test 3: Contact (avec QA intégré)
    print("\n3️⃣ Test Salesperson (avec QA)...")
    result = coord.contact_prospects(2, method="value_education")
    print(f"   Success: {result['success']}")
    
    print("\n" + "=" * 50)
    print("✅ Tests terminés")


if __name__ == "__main__":
    # Test ou usage direct
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_coordination()
    else:
        # Usage normal
        coord = AgentCoordinator()
        
        # Exemple: chercher prospects
        if "--search" in sys.argv:
            city_idx = sys.argv.index("--search") + 1
            city = sys.argv[city_idx]
            country = sys.argv[city_idx + 1] if len(sys.argv) > city_idx + 1 else None
            
            result = coord.prospect_search(city, country or "", 10)
            print(result['output'] if result['success'] else result['error'])
        
        # Exemple: contacter prospects
        elif "--contact" in sys.argv:
            result = coord.contact_prospects(5)
            print(result['output'] if result['success'] else result['error'])
        
        else:
            print("Usage:")
            print("  python3 agent_coordinator.py test")
            print("  python3 agent_coordinator.py --search Cusco Peru")
            print("  python3 agent_coordinator.py --contact")
