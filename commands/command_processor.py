# commands/command_processor.py

from notifications.whatsapp_notifier import send_whatsapp_message
from commands.change_command import handle_change_command, handle_add_command, handle_remove_command
from commands.discontinue_command import handle_discontinue_command
from commands.help_command import handle_help_command
from commands.update_command import (
    handle_updates_command,
    handle_court_updates_command,
)
import logging
from commands.message_parser import parse_change_command, parse_add_command, parse_remove_command
logger = logging.getLogger(__name__)

# Define Supported Commands
COMMANDS = {
    "update": "Get updates based on your preferences.",
    "help": "Show available commands.",
    "discontinue": "Unsubscribe from notifications.",
    "change": "Change preferences such as sports, notification timings, or days.",
    "updates on": "Get updates on specific courts.",
}


# --- Main Command Processor ---
# commands/command_processor.py



# commands/command_processor.py


def process_command(phone_number: str, command_text: str) -> None:
    try:
        command = command_text.lower().strip()

        if command.startswith("add"):
            result = parse_add_command(command_text)
            if result:
                handle_add_command(phone_number, result)
                return
        elif command.startswith("remove"):
            result = parse_remove_command(command_text)
            if result and "remove" in result:
                handle_remove_command(phone_number, result)
            else:
                send_whatsapp_message(
                    phone_number,
                    "Invalid command. Use the format:\n"
                    "- *remove cricket*\n"
                    "- *remove cricket, padel*\n"
                    "- *remove football and pickleball*"
                )
        # Handle Other Commands
        elif command.startswith("change"):
            handle_change_command(phone_number, command)
        elif command in ["update", "updates"]:
            handle_updates_command(phone_number)
        elif command.startswith(("updates on", "update on")):
            handle_court_updates_command(phone_number, command)
        elif command == "help":
            handle_help_command(phone_number)
        elif command == "discontinue":
            handle_discontinue_command(phone_number)
        else:
            send_whatsapp_message(
                phone_number, "Invalid command. Type *help* to see available commands."
            )
    except Exception as e:
        logger.error(f"Error processing command for {phone_number}: {e}")
