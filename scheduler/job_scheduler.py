# notification_scheduler.py

from apscheduler.triggers.cron import CronTrigger
from scheduler.scheduler_service import scheduler
from sheets.google_sheets import fetch_sheet_data
from utils.time_parser import parse_time
from notifications.whatsapp_notifier import send_whatsapp_message
import logging

logger = logging.getLogger(__name__)

# --- Notification Frequency Map ---
FREQUENCY_MAP = {
    "daily": "mon,tue,wed,thu,fri,sat,sun",
    "weekly": "mon",
    "twice a week": "mon,thu",
    "thrice a week": "mon,wed,fri",
}

# --- Schedule a Notification Job ---
def schedule_job(player: dict) -> str:
    try:
        phone_number = player["Phone Number"]
        job_id = f"{phone_number}_notification_job"
        notification_time = player["Notification Time"].strip("'")
        notification_frequency = player["Notification Frequency"].lower()

        # Parse time
        hour, minute = parse_time(notification_time)
        logger.info(f"Parsed time for {phone_number}: {hour}:{minute}")

        # Resolve days from frequency
        days = FREQUENCY_MAP.get(notification_frequency, "mon")
        logger.info(f"Scheduling for days: {days}")

        # Remove existing job if any
        if scheduler.get_job(job_id):
            logger.info(f"Removing existing job for {phone_number}.")
            scheduler.remove_job(job_id)

        # Schedule the job
        scheduler.add_job(
            func=_notify_player,
            trigger=CronTrigger(
                day_of_week=days, hour=hour, minute=minute
            ),
            id=job_id,
            args=[player],
            replace_existing=True,
        )

        logger.info(f"Scheduled job {job_id} successfully.")
        return job_id

    except Exception as e:
        logger.error(f"Error scheduling job for {phone_number}: {e}")
        raise


# --- Notify Player Function ---
def _notify_player(player: dict):
    phone_number = player["Phone Number"]
    player_name = player["Player Name"]

    logger.info(f"Preparing WhatsApp message for {phone_number} - {player_name}.")

    try:
        message_body = f"Hi {player_name}, this is your scheduled notification!"
        send_whatsapp_message(phone_number, message_body)
        logger.info(f"Message successfully sent to {phone_number}.")
    except Exception as e:
        logger.error(f"Failed to send message to {phone_number}: {e}")


# --- Schedule Notifications from Sheets ---
def schedule_notifications_from_sheets():
    try:
        players_df = fetch_sheet_data("player-response-sheet", "Players")

        if players_df.empty:
            logger.warning("No player data found in Google Sheets.")
            return

        # Iterate through players and schedule notifications
        for _, player in players_df.iterrows():
            schedule_job(player)

        logger.info("All notifications successfully scheduled.")
    except Exception as e:
        logger.error(f"Error fetching or scheduling notifications: {e}")
