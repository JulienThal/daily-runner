import os
from datetime import datetime, timedelta
from .leagues import LEAGUES
from .api_client import get_matches

def fetch_daily_results():
    # Récupération dynamique de l'API_KEY (après load_dotenv dans main.py)
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise RuntimeError("[ERREUR] API_KEY introuvable dans le fichier .env")

    date_to_fetch = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    results = {}

    for league in LEAGUES:
        league_name = league["name"]
        league_code = league["code"]

        print(f"Récupération : {league_name} ({date_to_fetch})")

        try:
            data = get_matches(league_code, date_to_fetch, api_key=api_key)
        except Exception as e:
            print(f"Erreur API pour {league_name}: {e}")
            data = []

        # Injection du nom officiel dans les données
        results[league_code] = {
            "name": league_name,
            "matches": data
        }

    return results
