# commands/update_command.py

from notifications.whatsapp_notifier import send_whatsapp_message
from sheets.google_sheets import (
    fetch_sheet_data, 
    fetch_not_booked_slots, 
    parse_date_from_sheet, 
    validate_slot_timing
)
from commands.message_parser import parse_change_command, parse_court_name
import logging
import pandas as pd

logger = logging.getLogger(__name__)

# --- Handle Updates Command ---
def handle_updates_command(phone_number: str) -> None:
    try:
        players_df = fetch_sheet_data("player-response-sheet", "Players")
        players_df["Phone Number"] = players_df["Phone Number"].apply(str).str.strip()

        # Check if the player exists
        player = players_df[players_df["Phone Number"] == phone_number]

        if player.empty:
            send_whatsapp_message(
                phone_number, 
                "You are not registered. Please contact support."
            )
            return

        # Extract player data and send updates
        player_data = player.iloc[0]
        send_latest_updates(player_data, phone_number)
    except Exception as e:
        logger.error(f"Error handling updates for {phone_number}: {e}")


# --- Handle Court-Specific Updates ---
def handle_court_updates_command(phone_number: str, command_text: str) -> None:
    try:
        # Extract and normalize the court name from the command
        court_name = parse_court_name(command_text)

        if not court_name:
            send_whatsapp_message(
                phone_number,
                "Invalid court name. Please try again or type *help* for available commands."
            )
            return

        # Fetch all available slots
        all_slots = fetch_not_booked_slots()

        if all_slots.empty:
            send_whatsapp_message(
                phone_number, 
                f"No available slots for {court_name} at the moment."
            )
            return

        # Filter matching slots by business name
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


# --- Send Latest Updates ---
def send_latest_updates(player, phone_number: str):
    try:
        # Fetch all available slots
        all_slots = fetch_not_booked_slots()

        if all_slots.empty:
            send_whatsapp_message(
                phone_number, 
                f"Hi {player['Player Name']}, no available slots match your preferences right now."
            )
            return

        # Match player preferences
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
            try:
                formatted_date = parse_date_from_sheet(slot["Date"])
                details.append(f"*Date*: {formatted_date}")
            except ValueError:
                details.append(f"*Date*: Invalid Date Format")
        else:
            details.append(f"*Date*: Not Provided")

        if "Timing" in slot and validate_slot_timing(slot["Timing"]):
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
