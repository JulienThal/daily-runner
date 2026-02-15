import json
import logging
import io
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pytz

# --- IMPORTS INTERNES ---
from src.config import ACTIVE_BATCHES, API_KEY, BASE_URL
from src.leagues import LEAGUES
from src.api_client import get_matches
from src.generate_image import generate_image
from src.drive_uploader import (
    upload_json_bytes,
    upload_png_bytes,
    drive_find_file_id,
    download_json_bytes_by_id
)

# ---------------------------------------------------------
# CONFIG LOGGING (console + buffer mémoire)
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler()]
)

log = logging.getLogger("pipeline")

# Buffer mémoire pour uploader le log dans Drive
log_buffer = io.StringIO()
buffer_handler = logging.StreamHandler(log_buffer)
buffer_handler.setLevel(logging.INFO)
buffer_handler.setFormatter(logging.Formatter("%(asctime)s — %(levelname)s — %(message)s"))
log.addHandler(buffer_handler)

# ---------------------------------------------------------
# GOOGLE DRIVE FOLDERS
# ---------------------------------------------------------
JSON_FOLDER_ID = "1odQ4ZzrNe6RKktbMOlGIbK_nebaxjcWI"
PNG_FOLDER_ID = "1hAOf_GrMsOAW1iwDkBdhVSMQKcgPFtr0"
LOGS_FOLDER_ID = "1L4GlV7oib27QkzHQtHBm5Pbma7vf9Vc9"

# Charger .env
load_dotenv()

# ---------------------------------------------------------
# UTILITAIRE : Sélection des ligues selon les batchs actifs
# ---------------------------------------------------------
def get_leagues_for_active_batches():
    return [
        league for league in LEAGUES
        if league["active"] == 1 and league["batch_id"] in ACTIVE_BATCHES
    ]

# ---------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------
if __name__ == "__main__":

    print("=== 🚀 DÉMARRAGE DU PIPELINE FOOTBALL ===")
    log.info("Pipeline démarré.")

    # ---------------------------------------------------------
    # Gestion du fuseau horaire France (Europe/Paris)
    # ---------------------------------------------------------
    paris = pytz.timezone("Europe/Paris")

    now_paris = datetime.now(paris)
    target_date = now_paris - timedelta(days=1)
    date_str = target_date.strftime("%Y-%m-%d")
    timestamp = now_paris.strftime("%Y-%m-%d_%H-%M-%S")

    json_filename = f"results_{date_str}.json"

    print(f"Heure locale France : {now_paris.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Date ciblée : {date_str}")

    log.info(f"Heure locale France : {now_paris.strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"Date ciblée : {date_str}")

    # ---------------------------------------------------------
    # 1) Vérification stricte par ID
    # ---------------------------------------------------------
    print("✔ Vérification du JSON dans Google Drive…")
    log.info("Recherche stricte du JSON dans Drive.")

    file_id = drive_find_file_id(json_filename, JSON_FOLDER_ID)

    if file_id:
        print(f"✔ Le fichier {json_filename} existe dans le dossier JSON.")
        print("→ Téléchargement du JSON pour générer les PNG…")
        log.info(f"JSON trouvé (ID={file_id}), téléchargement en cours.")

        json_bytes = download_json_bytes_by_id(file_id)
        resultat = json.loads(json_bytes.decode("utf-8"))

        print("📥 JSON téléchargé depuis Drive.")
        log.info("JSON téléchargé depuis Drive.")

    else:
        print("❌ JSON absent dans Google Drive → extraction API…")
        log.info("JSON absent dans Drive, extraction API en cours.")

        # ---------------------------------------------------------
        # 🔥 EXTRACTION PAR BATCHS
        # ---------------------------------------------------------
        print("📌 Sélection des ligues selon les batchs actifs…")
        log.info(f"Batchs actifs : {ACTIVE_BATCHES}")

        leagues_to_process = get_leagues_for_active_batches()

        # Récupération du batch utilisé (si plusieurs, on prend le premier)
        batch_number = ACTIVE_BATCHES[0] if ACTIVE_BATCHES else "X"

        print(f"→ Ligues à traiter : {[l['code'] for l in leagues_to_process]}")
        log.info(f"Ligues à traiter : {[l['code'] for l in leagues_to_process]}")

        resultat = {}

        for league in leagues_to_process:
            code = league["code"]
            name = league["name"]

            print(f"⚽ Extraction {name} ({code})…")
            log.info(f"Extraction {name} ({code})")

            data = get_matches(code, date_str)

            if data:
                # 🔥 Injection du nom officiel pour l'affichage dans generate_image()
                data["name"] = name
                resultat[code] = data
            else:
                print(f"[INFO] Aucun match ou erreur pour {code}")
                log.info(f"Aucun match ou erreur pour {code}")

        # Upload JSON
        json_bytes = json.dumps(resultat, indent=4, ensure_ascii=False).encode("utf-8")
        upload_json_bytes(json_bytes, json_filename, JSON_FOLDER_ID)

        print("✔ JSON uploadé dans Google Drive.")
        log.info("JSON uploadé dans Drive.")

    # ---------------------------------------------------------
    # 2) Génération des PNG
    # ---------------------------------------------------------
    print("🖼 Génération des images PNG…")
    log.info("Début de la génération des PNG.")

    png_files = generate_image(resultat, date_str)

    print(f"✔ {len(png_files)} pages générées.")
    log.info(f"{len(png_files)} pages PNG générées.")

    # ---------------------------------------------------------
    # 3) Upload PNG
    # ---------------------------------------------------------
    print("📤 Upload des PNG dans Google Drive…")
    log.info("Upload des PNG dans Drive.")

    for i, png_bytes in enumerate(png_files, start=1):
        filename = f"resultats_{date_str}_batch{batch_number}_page{i}-{len(png_files)}.png"
        upload_png_bytes(png_bytes, filename, PNG_FOLDER_ID)

        print(f"  → Page {i} uploadée.")
        log.info(f"PNG page {i} uploadé.")

    # ---------------------------------------------------------
    # 4) Upload du log horodaté
    # ---------------------------------------------------------
    print("📝 Upload du log dans Google Drive…")
    log.info("Upload du log dans Drive.")

    log_content = log_buffer.getvalue().encode("utf-8")
    log_filename = f"log_{timestamp}.txt"

    upload_json_bytes(
        log_content,
        log_filename,
        LOGS_FOLDER_ID
    )

    print(f"✔ Log uploadé : {log_filename}")
    log.info(f"Log uploadé dans Drive : {log_filename}")

    # ---------------------------------------------------------
    # FIN
    # ---------------------------------------------------------
    print("🎉 Pipeline cloud terminé — aucun fichier local utilisé.")
    log.info("Pipeline terminé avec succès.")
