from notifications.whatsapp_notifier import send_whatsapp_message
from scheduler.notification_scheduler import scheduler
import logging

logger = logging.getLogger(__name__)

def handle_discontinue_command(phone_number: str) -> None:
    try:
        job_id = f"{phone_number}_notification"

        # Remove job from scheduler
        scheduler.remove_job(job_id)
        logger.info(f"Successfully unsubscribed {phone_number} from notifications.")

        # Send confirmation message
        send_whatsapp_message(
            phone_number,
            "You have been successfully unsubscribed from notifications."
        )
    except Exception as e:
        logger.error(f"Error handling discontinue command for {phone_number}: {e}")
        send_whatsapp_message(
            phone_number, 
            "An error occurred while unsubscribing. Please try again later."
        )
