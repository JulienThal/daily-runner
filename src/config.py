import os
import sys
from dotenv import load_dotenv

# ---------------------------------------------------------
# Déterminer le dossier racine du projet
# ---------------------------------------------------------

if getattr(sys, "frozen", False):
    # Exécutable PyInstaller → dossier contenant l'exe
    ROOT_DIR = os.path.dirname(sys.executable)
else:
    # Script Python → remonter depuis src/ vers la racine
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------
# Charger le .env à la racine du projet
# ---------------------------------------------------------

ENV_PATH = os.path.join(ROOT_DIR, ".env")
load_dotenv(ENV_PATH)

API_KEY = os.getenv("API_KEY")
BASE_URL = "https://api.football-data.org/v4"

if not API_KEY:
    print(f"[ERREUR] API_KEY introuvable dans {ENV_PATH}")

# ---------------------------------------------------------
# Batchs actifs (modifiable manuellement)
# ---------------------------------------------------------
ACTIVE_BATCHES = [1, 2, 3, 7, 9, 13]
