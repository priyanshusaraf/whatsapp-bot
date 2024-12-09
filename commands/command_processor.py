# commands/command_processor.py

from notifications.whatsapp_notifier import send_whatsapp_message
from sheets.google_sheets import fetch_sheet_data, fetch_not_booked_slots
from scheduler.notification_scheduler import schedule_notification
import logging

logger = logging.getLogger(__name__)

# Define Supported Courts (Case-Insensitive)
COURT_ALIASES = {
    "turfxl": "TurfXL",
    "turf xl": "TurfXL",
    "playplex": "PlayPlex",
    "play plex": "PlayPlex",
    "turfedge": "TurfEdge",
    "turf edge": "TurfEdge",
    "padelclub": "PadelClub",
    "padel club": "PadelClub",
    "the padel club": "PadelClub",
}

# Available Commands
COMMANDS = {
    "update": "Get updates based on your preferences.",
    "help": "Show available commands.",
    "discontinue": "Unsubscribe from notifications.",
}

# --- Main Command Processor ---
def process_command(phone_number: str, command_text: str) -> None:
    try:
        command = command_text.lower().strip()

        if command in {"update", "updates"}:
            handle_updates_command(phone_number)
        elif command == "help":
            handle_help_command(phone_number)
        elif command == "discontinue":
            handle_discontinue_command(phone_number)
        elif command.startswith(("updates on", "update on")):
            handle_court_updates_command(phone_number, command)
        else:
            send_whatsapp_message(
                phone_number,
                "Invalid command. Type *help* to see available commands."
            )
    except Exception as e:
        logger.error(f"Error processing command for {phone_number}: {e}")


# --- Handle Player Updates ---
def handle_updates_command(phone_number: str) -> None:
    try:
        players_df = fetch_sheet_data("player-response-sheet", "Players")
        players_df["Phone Number"] = players_df["Phone Number"].apply(str).str.strip()

        player = players_df[players_df["Phone Number"] == phone_number]

        if player.empty:
            send_whatsapp_message(
                phone_number, 
                "You are not registered. Please contact support."
            )
            return

        player_data = player.iloc[0]
        send_latest_updates(player_data, phone_number)

    except Exception as e:
        logger.error(f"Error handling updates for {phone_number}: {e}")


# --- Send Latest Updates ---
def send_latest_updates(player, phone_number: str):
    try:
        all_slots = fetch_not_booked_slots()

        if all_slots.empty:
            send_whatsapp_message(
                phone_number, 
                f"Hi {player['Player Name']}, no available slots match your preferences right now."
            )
            return

        preferred_localities = [loc.strip().lower() for loc in player["Locality"].split(",")]
        preferred_sports = [sport.strip().lower() for sport in player["Preferences"].split(",")]

        matching_slots = all_slots[
            (all_slots["Locality"].isin(preferred_localities)) & 
            (all_slots["Sport"].isin(preferred_sports))
        ]

        if matching_slots.empty:
            send_whatsapp_message(
                phone_number, 
                f"Hi {player['Player Name']}, no available slots match your preferences right now."
            )
        else:
            message = construct_update_message(player["Player Name"], matching_slots)
            send_whatsapp_message(phone_number, message)

    except Exception as e:
        logger.error(f"Error fetching updates for {player['Player Name']}: {e}")


# --- Construct Update Message ---
def construct_update_message(player_name: str, slots_df) -> str:
    message = f"Hi {player_name}, here are the latest updates for your preferences:\n\n"
    for _, slot in slots_df.iterrows():
        message += (
            f"- *Business*: {slot['Business']} | *Sport*: {slot['Sport'].capitalize()} | "
            f"*Locality*: {slot['Locality'].capitalize()} | *Timing*: {slot['Timing']}\n"
        )
    return message


# --- Handle Court-Specific Updates ---
def handle_court_updates_command(phone_number: str, command_text: str) -> None:
    try:
        court_name_input = (
            command_text.lower()
            .replace("updates on", "")
            .replace("update on", "")
            .strip()
        )

        court_name = COURT_ALIASES.get(court_name_input)

        if not court_name:
            send_whatsapp_message(
                phone_number,
                "Invalid court name. Please try again or type *help* for available commands."
            )
            return

        all_slots = fetch_not_booked_slots()

        if all_slots.empty:
            send_whatsapp_message(
                phone_number, 
                f"No available slots for {court_name} at the moment."
            )
            return

        matching_slots = all_slots[
            all_slots["Business"].str.lower() == court_name.lower()
        ]

        if matching_slots.empty:
            send_whatsapp_message(
                phone_number,
                f"No available slots for {court_name} at the moment."
            )
        else:
            message = construct_update_message(court_name, matching_slots)
            send_whatsapp_message(phone_number, message)

    except Exception as e:
        logger.error(f"Error handling court updates for {phone_number}: {e}")


# --- Handle Help Command ---
def handle_help_command(phone_number: str) -> None:
    try:
        message = (
            "Available Commands:\n"
            "- *update*: Get notifications based on your preferences.\n"
            "- *help*: Show this message.\n"
            "- *discontinue*: Unsubscribe from updates.\n"
            "- *updates on [court]*: Get court-specific updates (e.g., updates on TurfXL).\n"
        )
        send_whatsapp_message(phone_number, message)
    except Exception as e:
        logger.error(f"Error handling help command for {phone_number}: {e}")


# --- Handle Discontinue Command ---
def handle_discontinue_command(phone_number: str) -> None:
    try:
        scheduler.remove_job(f"{phone_number}_notification")
        send_whatsapp_message(
            phone_number,
            "You have been successfully unsubscribed from notifications."
        )
    except Exception as e:
        logger.error(f"Error handling discontinue command for {phone_number}: {e}")
