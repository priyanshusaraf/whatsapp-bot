import pandas as pd
import logging
from .google_auth import gspread_client  # Import from the new file

logger = logging.getLogger(__name__)

# Normalize Phone Number
def normalize_phone_number(phone_number: str) -> str:
    phone_number_str = str(phone_number).strip()
    if not phone_number_str.startswith("+"):
        phone_number_str = f"+91{phone_number_str}"
    return phone_number_str

# Fetch Data from Google Sheets
def fetch_sheet_data(workspace_name: str, worksheet_name: str) -> pd.DataFrame:
    try:
        spreadsheet = gspread_client.open(workspace_name)
        worksheet = spreadsheet.worksheet(worksheet_name)
        data = worksheet.get_all_records()

        if not data:
            logger.warning(f"No records found in {workspace_name}/{worksheet_name}.")
            return pd.DataFrame()

        df = pd.DataFrame(data)
        if "Phone Number" in df.columns:
            df["Phone Number"] = df["Phone Number"].apply(normalize_phone_number)

        logger.info(f"Fetched {len(df)} records from {workspace_name}/{worksheet_name}.")
        return df
    except Exception as e:
        logger.error(f"Error fetching sheet data from {workspace_name}/{worksheet_name}: {e}")
        return pd.DataFrame()

# Fetch Not Booked Slots from Business Workspace
def fetch_not_booked_slots() -> pd.DataFrame:
    try:
        spreadsheet = gspread_client.open("business-workspace")
        all_business_data = []

        for sheet in spreadsheet.worksheets():
            data = sheet.get_all_records()
            if not data:
                continue

            df = pd.DataFrame(data)
            if {"Locality", "Sport", "Status"}.issubset(df.columns):
                df["Locality"] = df["Locality"].str.strip().str.lower()
                df["Sport"] = df["Sport"].str.strip().str.lower()
                df["Status"] = df["Status"].str.strip().str.lower()

                not_booked = df[df["Status"] == "not booked"].copy()
                not_booked["Business"] = sheet.title
                all_business_data.append(not_booked)

        return pd.concat(all_business_data, ignore_index=True) if all_business_data else pd.DataFrame()
    except Exception as e:
        logger.error(f"Error fetching business data: {e}")
        return pd.DataFrame()


def update_google_sheet(column_name: str, value: str, row_index: int) -> None:
    try:
        spreadsheet = gspread_client.open("player-response-sheet")
        worksheet = spreadsheet.worksheet("Players")

        headers = worksheet.row_values(1)
        if column_name not in headers:
            raise ValueError(f"Column '{column_name}' not found in the sheet.")

        column_index = headers.index(column_name) + 1  # 1-based index
        worksheet.update_cell(row_index, column_index, value)
        logger.info(f"Updated {column_name} to '{value}' for row {row_index} in Google Sheet.")
    except Exception as e:
        logger.error(f"Error updating {column_name} in Google Sheet: {e}")
        raise