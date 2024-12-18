import pandas as pd
from sheets.google_sheets import fetch_sheet_data, parse_date_from_sheet, validate_slot_timing
from notifications.whatsapp_notifier import send_whatsapp_message
from scheduler.notification_scheduler import schedule_notification
from utils.time_parser import parse_time
from datetime import datetime, time
import logging

logger = logging.getLogger(__name__)

VALID_FREQUENCIES = ["daily", "weekly", "twice a week", "thrice a week"]

# --- Check If Slot Is Valid ---
from datetime import datetime, time

# --- Check If Slot Is Valid ---
def is_valid_slot(row: pd.Series, notif_time_today: time, now: datetime) -> bool:
    """
    Validates if a given slot is upcoming and after the user's notification time.
    """
    try:
        # Validate Slot Timing
        if not validate_slot_timing(row["Timing"]):
            logger.error(f"Invalid slot timing format for row: {row}")
            return False

        # Parse Slot Date and Timing
        slot_date = parse_date_from_sheet(row["Date"])
        slot_date_obj = datetime.strptime(slot_date, "%d%B, %Y").date()

        # Extract Start Time of the Slot
        slot_start_time_str = row["Timing"].split("-")[0].strip()
        slot_start_time = datetime.strptime(slot_start_time_str, "%I:%M %p").time()

        # Current Date and Time
        current_date = now.date()
        current_time = now.time()

        # Check for Future Dates or Today’s Upcoming Slots
        if slot_date_obj > current_date:
            return True  # Future slots are valid

        if slot_date_obj == current_date:
            # Ensure Slot Start Time Is In The Future
            if current_time < slot_start_time and slot_start_time >= notif_time_today:
                return True

        return False

    except Exception as e:
        logger.error(f"Error processing row: {row} | Error: {e}")
        return False
  
# --- Filter Valid Slots ---
def filter_valid_slots(slots_df: pd.DataFrame, user_notification_time: str) -> pd.DataFrame:
    """
    Filters slots for upcoming dates and today's slots after the user's notification time.
    """
    try:
        user_notification_time = user_notification_time.strip("'")
        notif_time_today = datetime.strptime(user_notification_time, "%I:%M %p").time()
        now = datetime.now()

        # Apply the slot filtering logic
        valid_slots = slots_df[slots_df.apply(is_valid_slot, axis=1, args=(notif_time_today, now))].copy()

        # Ensure Dates Are Properly Formatted
        valid_slots["Date"] = valid_slots["Date"].apply(parse_date_from_sheet)
        logger.info(f"Filtered {len(valid_slots)} valid slots after applying timing logic.")
        return valid_slots

    except Exception as e:
        logger.error(f"Error filtering slots: {e}")
        return pd.DataFrame()

# --- Schedule Player Notification ---
def schedule_player_notification(player: pd.Series):
    try:
        phone_number_input = player["Phone Number"]
        notification_frequency = player["Notification Frequency"].strip().lower()
        notification_time = player["Notification Time"].strip()

        logger.info(f"Scheduling notifications for player: {player['Player Name']} | Phone: {phone_number_input}")

        schedule_notification(player, phone_number_input, notification_frequency, notification_time)
        logger.info(f"Successfully scheduled notifications for {player['Player Name']}")
    
    except Exception as e:
        logger.error(f"Failed to schedule notification for {player['Player Name']}: {e}")

# --- Process All Player Notifications ---
def process_player_notifications():
    try:
        # Fetch Player Data
        players_df = fetch_sheet_data("player-response-sheet", "Players")
        logger.info(f"Fetched {len(players_df)} player records from Google Sheets.")

        for _, player in players_df.iterrows():
            try:
                # Validate Player Data
                if not validate_player_data(player):
                    continue

                # Extract Data and Fetch Slots
                phone_number = str(player["Phone Number"]).strip()
                player_name = player["Player Name"].strip()
                notification_time = player["Notification Time"].strip()
                notification_frequency = player["Notification Frequency"].strip().lower()

                # Fetch Slots and Apply Filters
                slots_df = fetch_sheet_data("business-workspace", "Slots")
                valid_slots = filter_valid_slots(slots_df, notification_time)

                if valid_slots.empty:
                    logger.info(f"No valid slots for player {player_name}. Skipping notification.")
                    continue

                # Schedule Notifications
                job_id = schedule_notification(player, notification_frequency, notification_time)
                logger.info(f"Successfully scheduled notifications for {player_name} (Job ID: {job_id}).")

            except Exception as e:
                logger.error(f"Error processing player {player['Player Name']}: {e}")

    except Exception as e:
        logger.error(f"Error fetching player data from Google Sheets: {e}")

# --- Validate Player Data ---
def validate_player_data(player: pd.Series) -> bool:
    required_fields = ["Phone Number", "Notification Frequency", "Notification Time", 
                       "Player Name", "Preferences", "Locality"]
    missing_fields = [field for field in required_fields if field not in player or pd.isna(player[field])]

    if missing_fields:
        logger.error(f"Missing fields for player: {missing_fields}")
        return False

    if player["Notification Frequency"].strip().lower() not in VALID_FREQUENCIES:
        logger.error(f"Invalid frequency: {player['Notification Frequency']} for player {player['Player Name']}")
        return False

    return True
