# commands/help_command.py

from notifications.whatsapp_notifier import send_whatsapp_message
import logging

logger = logging.getLogger(__name__)

def handle_help_command(phone_number: str) -> None:
    try:
        # Help Message Content
        message = (
            "Available Commands:\n"
            "- *update*: Get notifications based on your preferences.\n"
            "- *help*: Show this message.\n"
            "- *discontinue*: Unsubscribe from updates.\n"
            "- *change sports from [old sports] to [new sports]*: Update sports preferences.\n"
            "- *add [sports]*: Add new sports to preferences.\n"
            "- *change notification timings from [old time] to [new time]*: Update notification timings.\n"
            "- *change notification day from [old days] to [new days]*: Update notification days.\n"
            "- *updates on [court name]*: Get court-specific updates (e.g., updates on TurfXL).\n"
        )

        # Send the help message to the user
        send_whatsapp_message(phone_number, message)
        logger.info(f"Sent help message to {phone_number}")
    except Exception as e:
        logger.error(f"Error handling help command for {phone_number}: {e}")
