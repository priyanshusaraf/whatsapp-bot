from scheduler.scheduler_service import scheduler
from apscheduler.triggers.cron import CronTrigger
from sheets.google_sheets import fetch_not_booked_slots, parse_date_from_sheet
from notifications.whatsapp_notifier import send_whatsapp_message
from utils.time_parser import parse_time
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# Booking Links
BUSINESS_LINKS = {
    "turfXL": "https://rebrand.ly/sy6d8zz",
    "PadelClub": "https://rebrand.ly/qd75mj9"
}

# Notification Frequency Mapping
FREQUENCY_TO_DAYS = {
    "daily": "mon,tue,wed,thu,fri,sat,sun",
    "weekly": "mon",
    "twice a week": "tue,thu",
    "thrice a week": "mon,wed,fri",
}

# Normalize Phone Number
def normalize_phone_number(phone_number):
    try:
        phone_number_str = str(phone_number).strip()
        if not phone_number_str.startswith("+"):
            phone_number_str = f"+91{phone_number_str}"
        return phone_number_str
    except Exception as e:
        logger.error(f"Error normalizing phone number {phone_number}: {e}")
        raise

# Notify Player Function
def _notify_player(player: dict, context=None):
    try:
        phone_number = normalize_phone_number(player["Phone Number"])
        player_name = player["Player Name"]

        logger.info(f"Fetching available slots for {player_name} ({phone_number}).")

        # Match Player with Available Slots
        matched_slots = match_player_with_slots(player)

        # Construct Notification Message
        if not matched_slots.empty:
            message_body = construct_update_message(player_name, matched_slots)
        else:
            message_body = f"Hi {player_name}, currently no available slots match your preferences."

        # Send the WhatsApp Message
        send_whatsapp_message(phone_number, message_body)
        logger.info(f"Notification sent successfully to {phone_number}.")

    except Exception as e:
        logger.error(f"Failed to send notification to {player_name} ({phone_number}): {e}")

# Schedule Notification Function
def schedule_notification(player: dict, notification_frequency: str, notification_time: str):
    try:
        # Validate and parse time
        hour, minute = parse_time(notification_time)
        logger.info(f"Parsed notification time: {hour}:{minute}")

        # Define Job ID
        phone_number = normalize_phone_number(player["Phone Number"])
        job_id = f"{phone_number}_notification"

        # Validate Frequency
        if notification_frequency.lower() not in FREQUENCY_TO_DAYS:
            raise ValueError(f"Invalid notification frequency: {notification_frequency}")

        # Remove existing job if present
        if scheduler.get_job(job_id):
            logger.info(f"Removing existing job {job_id}")
            scheduler.remove_job(job_id)

        # Schedule the Job
        scheduler.add_job(
            func=_notify_player,
            trigger=CronTrigger(
                day_of_week=FREQUENCY_TO_DAYS[notification_frequency.lower()],
                hour=hour,
                minute=minute,
            ),
            id=job_id,
            args=[player, None],  # Ensure context is passed
            replace_existing=True,
        )

        logger.info(f"Scheduled job {job_id} successfully.")
        return job_id

    except Exception as e:
        logger.error(f"Error scheduling notification for player {player['Player Name']}: {e}")
        raise

# Match Player with Available Slots
def match_player_with_slots(player: dict) -> pd.DataFrame:
    try:
        all_slots = fetch_not_booked_slots()

        if all_slots.empty:
            logger.warning("No available slots fetched from business sheets.")
            return pd.DataFrame()

        player_localities = [loc.strip().lower() for loc in player["Locality"].split(",")]
        player_preferences = [sport.strip().lower() for sport in player["Preferences"].split(",")]

        matched_slots = all_slots[
            (all_slots["Locality"].isin(player_localities)) & 
            (all_slots["Sport"].isin(player_preferences))
        ]

        logger.info(f"Matched slots for {player['Player Name']}:\n{matched_slots}")
        return matched_slots

    except Exception as e:
        logger.error(f"Error matching player {player['Player Name']} with slots: {e}")
        return pd.DataFrame()

logger = logging.getLogger(__name__)

# --- Construct WhatsApp Update Message ---
def construct_update_message(player_name: str, slots_df: pd.DataFrame) -> str:
    if slots_df.empty:
        return f"Hi {player_name}, currently no available slots match your preferences."

    message = f"Hi {player_name}, here are the latest updates for your preferences:\n\n"

    for _, slot in slots_df.iterrows():
        details = []

        # Add Slot Details
        if "Business" in slot:
            details.append(f"*Turf*: {slot['Business'].capitalize()}")

        if "Sport" in slot:
            details.append(f"*Sport*: {slot['Sport'].capitalize()}")

        if "Locality" in slot:
            details.append(f"*Area*: {slot['Locality'].capitalize()}")

        if "Date" in slot and slot["Date"] not in [None, ""]:
            formatted_date = parse_date_from_sheet(slot["Date"])
            details.append(f"*Date*: {formatted_date}")
        else:
            details.append(f"*Date*: Not Provided")

        if "Timing" in slot and slot["Timing"] not in [None, ""]:
            details.append(f"*Timing*: {slot['Timing']}")
        else:
            details.append(f"*Timing*: Invalid time format")

        if "Price" in slot and slot["Price"] not in [None, ""]:
            details.append(f"*Price*: ₹{slot['Price']}")
        else:
            details.append(f"*Price*: Not Provided")

        if "Booking" in slot and slot["Booking"] not in [None, ""]:
            details.append(f"👉 *Book Now*: {slot['Booking']}")
        else:
            details.append(f"👉 *Book Now*: Booking link not available")

        # Join details with ' | ' and append to the message
        message += " | ".join(details) + "\n\n"

    logger.debug(f"Constructed message:\n{message}")
    return message
