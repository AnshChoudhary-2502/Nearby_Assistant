import os

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.environ.get("CALENDAR_CREDENTIALS_FILE", os.path.join(_MODULE_DIR, "credentials.json"))
TOKEN_FILE = os.environ.get("CALENDAR_TOKEN_FILE", os.path.join(_MODULE_DIR, "token.json"))

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
]


def get_calendar_service():
    """Return an authenticated Google Calendar API service, running the OAuth
    consent flow once and reusing the cached refresh token afterwards."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)
