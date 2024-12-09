
import pandas as pd
from sheets.google_sheets import fetch_sheet_data
from notifications.whatsapp_notifier import send_whatsapp_message
from scheduler.notification_scheduler import schedule_notification
from utils.time_parser import parse_time
import logging

def schedule_player_notification(player: pd.Series):
    
    try:
        phone_number_input = player["Phone Number"]
        notification_frequency = player["Notification Frequency"].strip().lower()
        notification_time = player["Notification Time"].strip()

        logger.info(f"Scheduling notifications for player: {player['Player Name']} | Phone: {phone_number}")

        schedule_notification(player, phone_number_input, notification_frequency, notification_time)
        logger.info(f"Successfully scheduled notifications for {player['Player Name']}")
    
    except Exception as e:
        logger.error(f"Failed to schedule notification for {player['Player Name']}: {e}")


logger = logging.getLogger(__name__)

VALID_FREQUENCIES = ["daily", "weekly", "twice a week", "thrice a week"]

def process_player_notifications():
    try:
        # Fetch all player data
        players_df = fetch_sheet_data("player-response-sheet", "Players")
        logger.info(f"Fetched {len(players_df)} player records from Google Sheets.")

        for _, player in players_df.iterrows():
            try:
                phone_number = str(player["Phone Number"]).strip()
                player_name = player["Player Name"].strip()
                notification_frequency = player["Notification Frequency"].strip().lower()
                notification_time = player["Notification Time"].strip()

                # Validation Checks
                if not validate_player_data(player):
                    continue

                # Schedule Notifications
                job_id = schedule_notification(player, notification_frequency, notification_time)
                logger.info(f"Successfully scheduled notifications for {player_name} (Job ID: {job_id}).")


            except Exception as e:
                logger.error(f"Error processing player {player['Player Name']}: {e}")

    except Exception as e:
        logger.error(f"Error fetching player data from Google Sheets: {e}")


def validate_player_data(player: pd.Series) -> bool:
    required_fields = ["Phone Number", "Notification Frequency", "Notification Time", "Player Name", "Preferences", "Locality"]
    missing_fields = [field for field in required_fields if field not in player or pd.isna(player[field])]

    if missing_fields:
        logger.error(f"Missing fields for player: {missing_fields}")
        return False

    if player["Notification Frequency"].strip().lower() not in VALID_FREQUENCIES:
        logger.error(f"Invalid frequency: {player['Notification Frequency']} for player {player['Player Name']}")
        return False

    return True