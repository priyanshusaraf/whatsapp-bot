# notification_scheduler.py

from apscheduler.triggers.cron import CronTrigger
from scheduler.scheduler_service import scheduler
from sheets.google_sheets import fetch_sheet_data
from utils.time_parser import parse_time
import logging

logger = logging.getLogger(__name__)

def schedule_job(player: dict, message_body: str) -> str:

    try:
        phone_number = player["Phone Number"]
        job_id = f"{phone_number}_notification_job"
        hour, minute = parse_time(player["Notification Time"])

        frequency_map = {
            "daily": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "weekly": ["mon"],
            "twice a week": ["mon", "thu"],
            "thrice a week": ["mon", "wed", "fri"],
        }
        days = frequency_map.get(player["Notification Frequency"].lower(), ["mon"])

        scheduler.add_job(
            func=_notify_player,
            trigger=CronTrigger(day_of_week=",".join(days), hour=hour, minute=minute),
            id=job_id,
            args=[player, message_body],
            replace_existing=True,
        )

        logger.info(f"Scheduled job {job_id} successfully.")
        return job_id
    
    except Exception as e:
        logger.error(f"Error occurred while scheduling job: {e}")
        raise e


def _notify_player(player: dict, message_body: str):

    phone_number = player["Phone Number"]
    player_name = player["Player Name"]

    logger.info(f"Sending WhatsApp message to {phone_number} for {player_name}.")

    from notifications.whatsapp_notifier import send_whatsapp_message

    try:
        send_whatsapp_message(phone_number, message_body)
        logger.info(f"Message successfully sent to {phone_number}.")
    except Exception as e:
        logger.error(f"Failed to send message to {phone_number}: {e}")


def schedule_notifications_from_sheets():

    try:
        players_df = fetch_sheet_data("player-response-sheet", "Players")

        if players_df.empty:
            logger.warning("No player data found in Google Sheets.")
            return

        # Iterate through players and schedule notifications
        for _, player in players_df.iterrows():
            message_body = f"Hi {player['Player Name']}, this is your scheduled notification!"
            schedule_job(player, message_body)

        logger.info("All notifications successfully scheduled.")
    except Exception as e:
        logger.error(f"Error fetching or scheduling notifications: {e}")
