import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os
import logging

# Initialize Logger
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Google Sheets Configuration
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

# Validate Service Account File
if not SERVICE_ACCOUNT_FILE:
    raise EnvironmentError("Environment variable GOOGLE_SHEETS_CREDENTIALS is not set.")

if not os.path.exists(SERVICE_ACCOUNT_FILE):
    raise FileNotFoundError(f"Service account file not found: {SERVICE_ACCOUNT_FILE}")

# Authorize Google Sheets Client
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gspread_client = gspread.authorize(credentials)


# Normalize Phone Number
def normalize_phone_number(phone_number: str) -> str:
    """
    Ensure the phone number has country code +91.
    """
    phone_number_str = str(phone_number).strip()
    if not phone_number_str.startswith("+"):
        phone_number_str = f"+91{phone_number_str}"
    return phone_number_str


# Fetch Data from Google Sheets
def fetch_sheet_data(workspace_name: str, worksheet_name: str) -> pd.DataFrame:
    """Fetch data from a specified Google Sheets worksheet."""
    try:
        spreadsheet = gspread_client.open(workspace_name)
        worksheet = spreadsheet.worksheet(worksheet_name)
        data = worksheet.get_all_records()

        if not data:
            logger.warning(f"No records found in {workspace_name}/{worksheet_name}.")
            return pd.DataFrame()

        df = pd.DataFrame(data)

        # Normalize Phone Numbers
        if "Phone Number" in df.columns:
            df["Phone Number"] = df["Phone Number"].apply(normalize_phone_number)

        logger.info(f"Fetched {len(df)} records from {workspace_name}/{worksheet_name}.")
        return df
    except gspread.SpreadsheetNotFound:
        logger.error(f"Spreadsheet '{workspace_name}' not found.")
    except gspread.WorksheetNotFound:
        logger.error(f"Worksheet '{worksheet_name}' not found in '{workspace_name}'.")
    except Exception as e:
        logger.error(f"Unexpected error fetching sheet data from {workspace_name}/{worksheet_name}: {e}")
    return pd.DataFrame()


# Fetch Not Booked Slots from Business Workspace
def fetch_not_booked_slots() -> pd.DataFrame:
    """Fetch 'not booked' slots from all business sheets."""
    try:
        spreadsheet = gspread_client.open("business-workspace")
        all_business_data = []

        for sheet in spreadsheet.worksheets():
            logger.info(f"Processing sheet: {sheet.title}")
            data = sheet.get_all_records()

            if not data:
                logger.warning(f"No data in sheet {sheet.title}. Skipping.")
                continue

            df = pd.DataFrame(data)

            # Validate Required Columns
            required_columns = {"Locality", "Sport", "Status"}
            if not required_columns.issubset(df.columns):
                logger.error(f"Missing required columns in sheet {sheet.title}. Skipping.")
                continue

            # Normalize Data and Filter "Not Booked" Slots
            df["Locality"] = df["Locality"].str.strip().str.lower()
            df["Sport"] = df["Sport"].str.strip().str.lower()
            df["Status"] = df["Status"].str.strip().str.lower()

            not_booked = df[df["Status"] == "not booked"].copy()
            not_booked["Business"] = sheet.title
            all_business_data.append(not_booked)

        if all_business_data:
            all_slots = pd.concat(all_business_data, ignore_index=True)
            logger.info(f"Fetched {len(all_slots)} 'not booked' slots.")
            return all_slots
        else:
            logger.warning("No 'not booked' slots found in any business sheet.")
            return pd.DataFrame()

    except gspread.SpreadsheetNotFound:
        logger.error("Spreadsheet 'business-workspace' not found.")
    except Exception as e:
        logger.error(f"Unexpected error fetching business data: {e}")
    return pd.DataFrame()