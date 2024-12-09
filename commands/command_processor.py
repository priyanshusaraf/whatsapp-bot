# commands/command_processor.py

from notifications.whatsapp_notifier import send_whatsapp_message
from sheets.google_sheets import fetch_sheet_data, fetch_not_booked_slots
from scheduler.notification_scheduler import schedule_notification
import logging
from gspread import Worksheet
from sheets.google_sheets import gspread_client 
import re

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

COLUMN_MAPPING = {
    "Timestamp": 1,
    "Email address": 2,
    "Player Name": 3,
    "Phone Number": 4,
    "Preferences": 5,
    "Locality": 6,
    "Notification Frequency": 7,
    "Notification Time": 8,
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

        if command in ["update", "updates"]:
            handle_updates_command(phone_number)
        elif command.startswith("change"):
            handle_change_command(phone_number, command)
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


def handle_discontinue_command(phone_number: str) -> None:
    try:
        scheduler.remove_job(f"{phone_number}_notification")
        send_whatsapp_message(
            phone_number,
            "You have been successfully unsubscribed from notifications."
        )
    except Exception as e:
        logger.error(f"Error handling discontinue command for {phone_number}: {e}")




def update_google_sheet(column_name: str, value: str, row_index: int) -> None:
    try:
        # Open the Google Sheets document
        spreadsheet = gspread_client.open("player-response-sheet")
        worksheet = spreadsheet.worksheet("Players")

        # Get the column index for the given column name
        headers = worksheet.row_values(1)
        if column_name not in headers:
            raise ValueError(f"Column '{column_name}' not found in the sheet.")

        column_index = headers.index(column_name) + 1  # Convert 0-based to 1-based index

        # Update the cell
        worksheet.update_cell(row_index, column_index, value)
        logger.info(f"Updated {column_name} to '{value}' for row {row_index} in Google Sheet.")
    except Exception as e:
        logger.error(f"Error updating {column_name} in Google Sheet: {e}")
        raise

def handle_change_command(phone_number: str, command_text: str) -> None:
    """
    Handle the 'change' command to update user preferences.
    """
    try:
        # Fetch the player data
        players_df = fetch_sheet_data("player-response-sheet", "Players")
        players_df["Phone Number"] = players_df["Phone Number"].apply(str).str.strip()
        player = players_df[players_df["Phone Number"] == phone_number]

        if player.empty:
            send_whatsapp_message(
                phone_number,
                "You are not registered. Please contact support."
            )
            return

        # Extract the player's row index in the sheet
        player_data = player.iloc[0]
        row_index = player.index[0] + 2  # Adjust for header (1-based index)

        # Parse the command text
        updates = parse_change_command(command_text)
        if not updates:
            send_whatsapp_message(
                phone_number,
                "Invalid command. Use formats like:\n"
                "- change sports from pickleball and football to cricket\n"
                "- change notification timings from 10 am to 11 am\n"
                "- change notification day from Monday to Tuesday and Friday"
            )
            return

        # Process updates
        acknowledgment = []

        # Update Sports
        if "sports" in updates:
            sports_update = updates["sports"]
            if sports_update["action"] == "replace":
                update_google_sheet("Preferences", ", ".join(sports_update["new"]), row_index)
                acknowledgment.append(
                    f"Your sports preferences have been updated from "
                    f"{', '.join(sports_update['old'])} to {', '.join(sports_update['new'])}."
                )
            elif sports_update["action"] == "add":
                current_preferences = player_data["Preferences"].split(", ")
                updated_preferences = list(set(current_preferences + sports_update["new"]))
                update_google_sheet("Preferences", ", ".join(updated_preferences), row_index)
                acknowledgment.append(
                    f"Added new sports to your preferences: {', '.join(sports_update['new'])}. "
                    f"Your updated preferences are: {', '.join(updated_preferences)}."
                )

        # Update Timing
        if "timing" in updates:
            timing_update = updates["timing"]
            update_google_sheet("Notification Time", timing_update["new"], row_index)
            acknowledgment.append(
                f"Your notification timing has been updated from {timing_update['old']} to {timing_update['new']}."
            )

        # Update Days
        if "days" in updates:
            day_update = updates["days"]
            update_google_sheet("Notification Frequency", ", ".join(day_update["new"]), row_index)
            acknowledgment.append(
                f"Your notification days have been updated from {', '.join(day_update['old'])} to {', '.join(day_update['new'])}."
            )

        # Send acknowledgment
        if acknowledgment:
            send_whatsapp_message(
                phone_number,
                "Your updates have been successfully processed:\n" + "\n".join(acknowledgment)
            )

    except Exception as e:
        logger.error(f"Error handling change command for {phone_number}: {e}")
        send_whatsapp_message(
            phone_number, "An error occurred while processing your request. Please try again later."
        )


def parse_change_command(command_text: str) -> dict:
    updates = {}

    # Lowercase and strip the command for consistent parsing
    command = command_text.lower().strip()

    # Handle 'change sports from ... to ...'
    sports_change_match = re.search(
        r"change sports from ([a-z, and]+) to ([a-z, and]+)", command
    )
    if sports_change_match:
        old_sports_raw = sports_change_match.group(1)
        new_sports_raw = sports_change_match.group(2)

        # Normalize sports by splitting on "and," "or," or commas
        old_sports = re.split(r",| and | or ", old_sports_raw)
        old_sports = [s.strip().capitalize() for s in old_sports if s.strip()]

        new_sports = re.split(r",| and | or ", new_sports_raw)
        new_sports = [s.strip().capitalize() for s in new_sports if s.strip()]

        updates["sports"] = {
            "action": "replace",
            "old": old_sports,
            "new": new_sports,
        }

    # Handle 'add sports ...'
    sports_add_match = re.search(r"add ([a-z, and]+)", command)
    if sports_add_match:
        additional_sports_raw = sports_add_match.group(1)

        # Normalize sports by splitting on "and," "or," or commas
        additional_sports = re.split(r",| and | or ", additional_sports_raw)
        additional_sports = [
            s.strip().capitalize() for s in additional_sports if s.strip()
        ]

        updates["sports"] = {
            "action": "add",
            "new": additional_sports,
        }

    # Handle 'change notification timings from ... to ...'
    timing_change_match = re.search(
        r"change notification timings from ([a-z0-9: ]+ [ap]m) to ([a-z0-9: ]+ [ap]m)",
        command,
    )
    if timing_change_match:
        old_timing = timing_change_match.group(1).strip()
        new_timing = timing_change_match.group(2).strip()
        updates["timing"] = {"old": old_timing, "new": new_timing}

    # Handle 'change notification day from ... to ...'
    day_change_match = re.search(
        r"change notification day from ([a-z, and]+) to ([a-z, and]+)", command
    )
    if day_change_match:
        old_days_raw = day_change_match.group(1)
        new_days_raw = day_change_match.group(2)

        # Normalize days by splitting on "and," "or," or commas
        old_days = re.split(r",| and | or ", old_days_raw)
        old_days = [d.strip().capitalize() for d in old_days if d.strip()]

        new_days = re.split(r",| and | or ", new_days_raw)
        new_days = [d.strip().capitalize() for d in new_days if d.strip()]

        updates["days"] = {"old": old_days, "new": new_days}

    return updates
