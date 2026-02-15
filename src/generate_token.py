from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_secrets_file(
    "credentials_oauth.json",
    ["https://www.googleapis.com/auth/drive"]
)
creds = flow.run_local_server(port=0)

print(creds.to_json())
