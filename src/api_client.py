import os
import time
import requests
from requests.exceptions import RequestException, Timeout

from src.config import API_KEY, BASE_URL


def get_matches(league_code, date, retries=3, timeout=10):
    """
    Récupère les matchs d'une ligue pour une date donnée.
    Gère :
    - soft-ban (403 / 429)
    - backoff exponentiel
    - JSON vide
    - erreurs API
    """

    if not API_KEY:
        raise RuntimeError("[ERREUR] API_KEY introuvable dans .env")

    url = f"{BASE_URL}/competitions/{league_code}/matches?dateFrom={date}&dateTo={date}"
    headers = {"X-Auth-Token": API_KEY}

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)

            # -------------------------------
            # 🔥 Détection SOFT-BAN
            # -------------------------------
            if response.status_code in (403, 429):
                wait = attempt * 5
                print(f"[SOFT-BAN] {league_code} → pause {wait}s…")
                time.sleep(wait)
                continue

            # -------------------------------
            # 🔥 Erreur HTTP classique
            # -------------------------------
            response.raise_for_status()

            data = response.json()

            # -------------------------------
            # 🔸 JSON vide
            # -------------------------------
            if not data or "matches" not in data:
                print(f"[INFO] Aucun match trouvé pour {league_code} le {date}")
                return {}

            # -------------------------------
            # 🔸 Message d’erreur dans la réponse
            # -------------------------------
            if isinstance(data, dict) and "error" in data:
                print(f"[ERREUR API] {league_code} : {data['error']}")
                return {}

            return data

        except Timeout:
            print(f"[TIMEOUT] Tentative {attempt}/{retries} pour {league_code}")

        except RequestException as e:
            print(f"[ERREUR API] {league_code} (tentative {attempt}/{retries}) : {e}")

    # -------------------------------
    # ❌ Échec après retries
    # -------------------------------
    print(f"[ECHEC] Impossible de récupérer les données pour {league_code} après {retries} tentatives.")
    return {}
