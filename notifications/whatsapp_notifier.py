from notifications.twilio_client import twilio_client, TWILIO_SANDBOX_NUMBER
import logging
import time

logger = logging.getLogger(__name__)

def send_whatsapp_message(to: str, message: str, retries: int = 3, delay: int = 5) -> None:
    attempt = 0

    while attempt < retries:
        try:
            twilio_client.messages.create(
                from_=f"whatsapp:{TWILIO_SANDBOX_NUMBER}",
                body=message,
                to=f"whatsapp:{to}"
            )
            logger.info(f"Message successfully sent to {to}")
            return
        except Exception as e:
            attempt += 1
            logger.error(f"Attempt {attempt}: Failed to send message to {to}. Error: {e}")

            if attempt < retries:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)

    logger.error(f"All attempts failed. Could not send message to {to}.")
