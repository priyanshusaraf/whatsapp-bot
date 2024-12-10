# sheets/google_auth.py

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Google Sheets Configuration
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Validate Service Account File
if not SERVICE_ACCOUNT_FILE:
    raise EnvironmentError("Environment variable GOOGLE_SHEETS_CREDENTIALS is not set.")

if not os.path.exists(SERVICE_ACCOUNT_FILE):
    raise FileNotFoundError(f"Service account file not found: {SERVICE_ACCOUNT_FILE}")

# Authorize Google Sheets Client
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gspread_client = gspread.authorize(credentials)

# Google Sheets API Client
google_sheet_service = build("sheets", "v4", credentials=credentials)
