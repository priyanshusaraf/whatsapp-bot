# sheets/google_sheets.py

import pandas as pd
import logging
from .google_auth import gspread_client
from datetime import datetime

logger = logging.getLogger(__name__)

# --- Normalize Phone Number ---
def normalize_phone_number(phone_number: str) -> str:
    phone_number_str = str(phone_number).strip()
    if not phone_number_str.startswith("+"):
        phone_number_str = f"+91{phone_number_str}"
    return phone_number_str


# --- Fetch Data from Google Sheets ---
def fetch_sheet_data(workspace_name: str, worksheet_name: str) -> pd.DataFrame:
    """
    Fetches all data from a specified Google Sheet worksheet and returns a DataFrame.
    """
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


# --- Fetch Not Booked Slots from Business Workspace ---
def fetch_not_booked_slots() -> pd.DataFrame:
    """
    Fetches 'Not Booked' slots from all sheets in the business workspace.
    """
    try:
        spreadsheet = gspread_client.open("business-workspace")
        all_business_data = []

        for sheet in spreadsheet.worksheets():
            try:
                # Fetch records
                data = sheet.get_all_records()
                if not data:
                    logger.info(f"No data found in sheet {sheet.title}.")
                    continue

                # Convert to DataFrame
                df = pd.DataFrame(data)
                
                # Validate required columns
                required_columns = {"Locality", "Sport", "Status"}
                if not required_columns.issubset(df.columns):
                    logger.warning(f"Missing required columns in sheet {sheet.title}. Skipping...")
                    continue

                # Normalize and filter data
                df["Locality"] = df["Locality"].astype(str).str.strip().str.lower()
                df["Sport"] = df["Sport"].astype(str).str.strip().str.lower()
                df["Status"] = df["Status"].astype(str).str.strip().str.lower()

                not_booked = df[df["Status"] == "not booked"].copy()
                if not not_booked.empty:
                    not_booked["Business"] = sheet.title
                    all_business_data.append(not_booked)
                else:
                    logger.info(f"No 'Not Booked' slots in sheet {sheet.title}.")
            except Exception as sheet_error:
                logger.error(f"Error processing sheet {sheet.title}: {sheet_error}")

        if all_business_data:
            result_df = pd.concat(all_business_data, ignore_index=True)
            logger.info(f"Fetched {len(result_df)} 'Not Booked' slots.")
            return result_df
        else:
            logger.info("No 'Not Booked' slots found across all sheets.")
            return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error fetching business data: {e}")
        return pd.DataFrame()

# --- Format Notification Time ---
def format_notification_time(time_str: str) -> str:
    """
    Formats the notification time to a consistent format like `'10:00 AM`.
    """
    try:
        parsed_time = datetime.strptime(time_str.strip().lower(), "%I:%M %p")
        formatted_time = f"'{parsed_time.strftime('%I:%M %p')}"
        logger.info(f"Formatted time: {formatted_time}")
        return formatted_time
    except ValueError as e:
        logger.error(f"Failed to format time '{time_str}': {e}")
        raise ValueError(f"Invalid time format: {time_str}")


# --- Update Google Sheet using gspread ---
def update_google_sheet(column_name: str, value: str, row_index: int) -> None:
    """
    Updates the specified column in the Google Sheet with the provided value.
    Dynamically finds the column index and applies formatting when necessary.
    """
    try:
        spreadsheet = gspread_client.open("player-response-sheet")
        worksheet = spreadsheet.worksheet("Players")

        # Format time if updating the Notification Time
        if column_name.lower() == "notification time":
            value = format_notification_time(value)

        # Find the column index dynamically
        header = worksheet.row_values(1)
        if column_name not in header:
            raise ValueError(f"Column '{column_name}' not found in the worksheet.")

        col_index = header.index(column_name) + 1

        # Update the Google Sheet
        worksheet.update_cell(row_index, col_index, value)
        logger.info(f"Updated {column_name} to '{value}' for row {row_index} in Google Sheet.")

    except Exception as e:
        logger.error(f"Error updating Google Sheet: {e}")
        raise
