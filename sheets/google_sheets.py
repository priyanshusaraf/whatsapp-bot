import pandas as pd
import logging
from .google_auth import gspread_client
from datetime import datetime
import re
logger = logging.getLogger(__name__)

# --- Normalize Phone Number ---
def normalize_phone_number(phone_number: str) -> str:
    phone_number_str = str(phone_number).strip()
    if not phone_number_str.startswith("+"):
        phone_number_str = f"+91{phone_number_str}"
    return phone_number_str
def validate_slot_timing(timing_str: str) -> bool:
    """
    Validates if the slot timing is in the correct format: 
    "6:00PM - 7:00PM" or "6:00 PM - 7:00 PM".
    """
    try:
        start_time, end_time = timing_str.replace(" ", "").split("-")
        datetime.strptime(start_time, "%I:%M%p")
        datetime.strptime(end_time, "%I:%M%p")
        return True
    except ValueError:
        logger.error(f"Invalid slot timing format: '{timing_str}'")
        return False

# --- Parse Date from Sheet ---
def parse_date_from_sheet(date_str: str) -> str:
    """
    Parses multiple date formats from Google Sheets and formats them as:
    "18th December, 2024", "1st January, 2024", etc.
    """
    try:
        cleaned_date_str = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", date_str.strip())
        supported_formats = [
            "%d %B, %Y", "%d %B %Y", 
            "%d-%m-%Y", "%d/%m/%Y", 
            "%d-%m-%y", "%d/%m/%y"
        ]

        parsed_date = None
        for fmt in supported_formats:
            try:
                parsed_date = datetime.strptime(cleaned_date_str, fmt)
                break
            except ValueError:
                continue

        if not parsed_date:
            raise ValueError(f"Date format not supported: {date_str}")

        day = parsed_date.day
        month = parsed_date.strftime("%B")
        year = parsed_date.year
        day_suffix = get_day_suffix(day)

        formatted_date = f"{day}{day_suffix} {month}, {year}"
        return formatted_date

    except Exception as e:
        raise ValueError(f"Error parsing date '{date_str}': {e}")

# --- Helper Function for Day Suffix ---
def get_day_suffix(day: int) -> str:
    """
    Returns the correct day suffix for a given day number.
    Example: 1 -> "st", 2 -> "nd", 3 -> "rd", 4+ -> "th"
    """
    if 11 <= day <= 13:
        return "th"
    last_digit = day % 10
    if last_digit == 1:
        return "st"
    elif last_digit == 2:
        return "nd"
    elif last_digit == 3:
        return "rd"
    else:
        return "th"
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
            sheet_name = sheet.title.strip().lower()
            logger.debug(f"Processing sheet: '{sheet_name}'")

            try:
                data = sheet.get_all_records()
                if not data:
                    logger.info(f"No data found in sheet '{sheet.title}'.")
                    continue

                df = pd.DataFrame(data)

                # Ensure Required Columns Exist
                required_columns = {"Locality", "Sport", "Status", "Date", "Timing", "Price", "Booking"}
                missing_columns = required_columns - set(df.columns)

                if missing_columns:
                    logger.warning(f"Sheet '{sheet.title}' missing columns: {', '.join(missing_columns)}.")

                # Normalize Relevant Columns
                if "Locality" in df.columns:
                    df["Locality"] = df["Locality"].astype(str).str.strip().str.lower()
                if "Sport" in df.columns:
                    df["Sport"] = df["Sport"].astype(str).str.strip().str.lower()
                if "Status" in df.columns:
                    df["Status"] = df["Status"].astype(str).str.strip().str.lower()

                # Filter for Not Booked Slots
                if "Status" in df.columns:
                    not_booked = df[df["Status"] == "not booked"].copy()
                    if not not_booked.empty:
                        not_booked["Business"] = sheet_name
                        all_business_data.append(not_booked)
                    else:
                        logger.info(f"No 'Not Booked' slots in sheet '{sheet.title}'.")

            except Exception as sheet_error:
                logger.error(f"Error processing sheet '{sheet.title}': {sheet_error}")

        if all_business_data:
            result_df = pd.concat(all_business_data, ignore_index=True)
            logger.info(f"Fetched {len(result_df)} 'Not Booked' slots with details.")
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
    Formats the notification time to a consistent format like `'10:00 AM'`.
    """
    try:
        parsed_time = datetime.strptime(time_str.strip().lower(), "%I:%M %p")
        formatted_time = f"'{parsed_time.strftime('%I:%M %p')}'"
        logger.info(f"Formatted time: {formatted_time}")
        return formatted_time
    
    except ValueError as e:
        logger.error(f"Failed to format time '{time_str}': {e}")
        raise ValueError(f"Invalid time format: {time_str}")


# --- Update Google Sheet using gspread ---
def update_google_sheet(column_name: str, value: str, row_index: int) -> None:
    try:
        spreadsheet = gspread_client.open("player-response-sheet")
        worksheet = spreadsheet.worksheet("Players")

        # Format time if updating the Notification Time
        if column_name.lower() == "notification time":
            value = format_notification_time(value)

        # Find the Column Index Dynamically
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

