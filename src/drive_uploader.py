import os
import io
import json

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from googleapiclient.discovery import build
from googleapiclient.http import (
    MediaFileUpload,
    MediaIoBaseUpload,
    MediaIoBaseDownload
)

# ---------------------------------------------------------
# Scopes : accès en lecture/écriture aux fichiers Drive
# ---------------------------------------------------------
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

TOKEN_PATH = "token.json"
OAUTH_CREDENTIALS_PATH = "credentials_oauth.json"


# ---------------------------------------------------------
# Service Drive (local + GitHub Actions)
# ---------------------------------------------------------
def _get_service():
    """
    Fonction hybride :
    - En local : utilise credentials_oauth.json + token.json
    - Dans GitHub Actions : utilise les secrets d'environnement
    """

    # -----------------------------------------------------
    # 1) MODE LOCAL : credentials_oauth.json existe
    # -----------------------------------------------------
    if os.path.exists(OAUTH_CREDENTIALS_PATH):
        print("[INFO] Mode local : OAuth via credentials_oauth.json")

        creds = None

        # Token existant ?
        if os.path.exists(TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

        # Token absent ou invalide → relancer OAuth
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    OAUTH_CREDENTIALS_PATH,
                    SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Sauvegarde du token
            with open(TOKEN_PATH, "w", encoding="utf-8") as token_file:
                token_file.write(creds.to_json())

        return build("drive", "v3", credentials=creds)

    # -----------------------------------------------------
    # 2) MODE GITHUB ACTIONS : utiliser les secrets
    # -----------------------------------------------------
    print("[INFO] Mode GitHub Actions : OAuth via secrets GitHub")

    creds_data = {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "refresh_token": os.getenv("GOOGLE_REFRESH_TOKEN"),
        "token_uri": "https://oauth2.googleapis.com/token"
    }

    creds = Credentials.from_authorized_user_info(creds_data)
    return build("drive", "v3", credentials=creds)


# ---------------------------------------------------------
# Upload local JSON
# ---------------------------------------------------------
def upload_to_drive(local_path, drive_filename=None, folder_id=None):
    service = _get_service()

    if drive_filename is None:
        drive_filename = os.path.basename(local_path)

    metadata = {"name": drive_filename}
    if folder_id:
        metadata["parents"] = [folder_id]

    media = MediaFileUpload(local_path, mimetype="application/json")

    uploaded = service.files().create(
        body=metadata,
        media_body=media,
        fields="id"
    ).execute()

    print(f"📤 Upload réussi — ID Drive : {uploaded['id']}")
    return uploaded["id"]


# ---------------------------------------------------------
# Upload local PNG
# ---------------------------------------------------------
def upload_png_to_drive(local_path, folder_id=None):
    service = _get_service()

    filename = os.path.basename(local_path)

    metadata = {"name": filename}
    if folder_id:
        metadata["parents"] = [folder_id]

    media = MediaFileUpload(local_path, mimetype="image/png")

    uploaded = service.files().create(
        body=metadata,
        media_body=media,
        fields="id"
    ).execute()

    print(f"📤 PNG uploadé — {filename} — ID : {uploaded['id']}")
    return uploaded["id"]


# ---------------------------------------------------------
# Vérifier si un fichier existe dans Drive
# ---------------------------------------------------------
def drive_file_exists(filename, folder_id=None):
    service = _get_service()

    query = f"name = '{filename}'"
    if folder_id:
        query += f" and '{folder_id}' in parents"

    results = service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name)"
    ).execute()

    return len(results.get("files", [])) > 0


# ---------------------------------------------------------
# Upload JSON en mémoire
# ---------------------------------------------------------
def upload_json_bytes(json_bytes, filename, folder_id=None):
    service = _get_service()

    metadata = {"name": filename}
    if folder_id:
        metadata["parents"] = [folder_id]

    media = MediaIoBaseUpload(io.BytesIO(json_bytes), mimetype="application/json")

    uploaded = service.files().create(
        body=metadata,
        media_body=media,
        fields="id"
    ).execute()

    print(f"📤 JSON uploadé — ID : {uploaded['id']}")
    return uploaded["id"]


# ---------------------------------------------------------
# Upload PNG en mémoire
# ---------------------------------------------------------
def upload_png_bytes(png_bytes, filename, folder_id=None):
    service = _get_service()

    metadata = {"name": filename}
    if folder_id:
        metadata["parents"] = [folder_id]

    media = MediaIoBaseUpload(io.BytesIO(png_bytes), mimetype="image/png")

    uploaded = service.files().create(
        body=metadata,
        media_body=media,
        fields="id"
    ).execute()

    print(f"📤 PNG uploadé — {filename} — ID : {uploaded['id']}")
    return uploaded["id"]


# ---------------------------------------------------------
# Télécharger un JSON depuis Drive (en mémoire)
# ---------------------------------------------------------
def download_json_bytes(filename, folder_id):
    service = _get_service()

    query = f"name = '{filename}' and '{folder_id}' in parents"
    results = service.files().list(q=query, fields="files(id)").execute()
    files = results.get("files", [])

    if not files:
        raise FileNotFoundError(f"Fichier {filename} introuvable dans Drive.")

    file_id = files[0]["id"]

    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)

    done = False
    while not done:
        _, done = downloader.next_chunk()

    buffer.seek(0)
    return buffer.getvalue()


# ---------------------------------------------------------
# Trouver un fichier par nom + dossier
# ---------------------------------------------------------
def drive_find_file_id(filename, folder_id):
    service = _get_service()

    query = (
        f"name = '{filename}' "
        f"and '{folder_id}' in parents "
        f"and trashed = false"
    )

    results = service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name, parents)"
    ).execute()

    files = results.get("files", [])

    if not files:
        return None

    return files[0]["id"]


# ---------------------------------------------------------
# Télécharger un JSON par ID (en mémoire)
# ---------------------------------------------------------
def download_json_bytes_by_id(file_id):
    service = _get_service()

    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)

    done = False
    while not done:
        _, done = downloader.next_chunk()

    buffer.seek(0)
    return buffer.getvalue()
