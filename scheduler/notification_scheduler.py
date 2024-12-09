from scheduler.scheduler_service import scheduler
from apscheduler.triggers.cron import CronTrigger
from sheets.google_sheets import fetch_not_booked_slots
from notifications.whatsapp_notifier import send_whatsapp_message
from utils.time_parser import parse_time
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# Notification Frequency Mapping
FREQUENCY_TO_DAYS = {
    "daily": "mon,tue,wed,thu,fri,sat,sun",
    "weekly": "mon",
    "twice a week": "tue,thu",
    "thrice a week": "mon,wed,fri",
}

# Normalize Phone Number
def normalize_phone_number(phone_number):
    """
    Ensure the phone number is a string and format it correctly.
    """
    try:
        phone_number_str = str(phone_number).strip()
        if not phone_number_str.startswith("+"):
            phone_number_str = f"+91{phone_number_str}"
        return phone_number_str
    except Exception as e:
        logger.error(f"Error normalizing phone number {phone_number}: {e}")
        raise

# Notify Player Function
def _notify_player(player: dict, _):
    """
    Fetch matching slots and send a WhatsApp message.
    """
    try:
        phone_number = normalize_phone_number(player["Phone Number"])
        player_name = player["Player Name"]

        logger.info(f"Fetching available slots for {player_name} ({phone_number}).")

        # Match Player with Available Slots
        matched_slots = match_player_with_slots(player)

        # Construct Notification Message
        if not matched_slots.empty:
            message_body = construct_business_message(player_name, matched_slots)
        else:
            message_body = f"Hi {player_name}, currently no available slots match your preferences."

        # Send the WhatsApp Message
        send_whatsapp_message(phone_number, message_body)
        logger.info(f"Notification sent successfully to {phone_number}.")

    except Exception as e:
        logger.error(f"Failed to send notification to {player['Player Name']} ({phone_number}): {e}")

# Schedule Notification Function
def schedule_notification(player: dict, notification_frequency: str, notification_time: str):
    """
    Schedule a WhatsApp notification based on player's preferences.
    """
    try:
        # Validate and parse time
        hour, minute = parse_time(notification_time)
        logger.info(f"Parsed notification time: {hour}:{minute}")

        # Define Job ID
        phone_number = normalize_phone_number(player["Phone Number"])
        job_id = f"{phone_number}_notification"

        # Validate Frequency
        if notification_frequency not in FREQUENCY_TO_DAYS:
            raise ValueError(f"Invalid notification frequency: {notification_frequency}")

        # Schedule the Job
        scheduler.add_job(
            func=_notify_player,
            trigger=CronTrigger(
                day_of_week=FREQUENCY_TO_DAYS[notification_frequency],
                hour=hour,
                minute=minute,
            ),
            id=job_id,
            args=[player, None],
            replace_existing=True,
        )

        logger.info(f"Scheduled job {job_id} successfully.")
        return job_id

    except Exception as e:
        logger.error(f"Error scheduling notification for player {player['Player Name']}: {e}")
        raise

# Match Player with Available Slots
def match_player_with_slots(player: dict) -> pd.DataFrame:
    """
    Match available slots from Google Sheets with player preferences.
    """
    try:
        all_slots = fetch_not_booked_slots()

        if all_slots.empty:
            logger.warning("No available slots fetched from business sheets.")
            return pd.DataFrame()

        # Normalize Player Preferences
        player_localities = [loc.strip().lower() for loc in player["Locality"].split(",")]
        player_preferences = [sport.strip().lower() for sport in player["Preferences"].split(",")]

        # Filter Matching Slots
        matched_slots = all_slots[
            (all_slots["Locality"].isin(player_localities)) & 
            (all_slots["Sport"].isin(player_preferences))
        ]

        logger.info(f"Matched slots for {player['Player Name']}:\n{matched_slots}")
        return matched_slots

    except Exception as e:
        logger.error(f"Error matching player {player['Player Name']} with slots: {e}")
        return pd.DataFrame()

# Construct WhatsApp Message
def construct_business_message(player_name: str, matched_slots: pd.DataFrame) -> str:
    """
    Construct a personalized WhatsApp message for the player.
    """
    if matched_slots.empty:
        return f"Hi {player_name}, currently no available slots match your preferences."

    message = f"Hi {player_name}, here are your latest available slots:\n\n"
    for _, slot in matched_slots.iterrows():
        message += (
            f"• {slot['Business']} ({slot['Sport']}): "
            f"{slot['Locality']} at {slot['Timing']}\n"
        )

    message += "\nPlease book your preferred slot at the earliest!"
    return message
