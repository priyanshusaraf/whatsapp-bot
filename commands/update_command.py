# commands/update_command.py

from notifications.whatsapp_notifier import send_whatsapp_message
from sheets.google_sheets import fetch_sheet_data, fetch_not_booked_slots
import logging

logger = logging.getLogger(__name__)

# Court Aliases (Case-Insensitive)
COURT_ALIASES = {
    "turfxl": "turfXL",
    "playplex": "PlayPlex",
    "turfedge": "TurfEdge",
    "padelclub": "The Padel Club",
}

# Booking Links
BUSINESS_LINKS = {
    "turfXL": "https://rebrand.ly/sy6d8zz",
    "PadelClub": "https://rebrand.ly/qd75mj9",
}

# --- Handle Update Command ---
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
        court_name_input = (
            command_text.lower()
            .replace("updates on", "")
            .replace("update on", "")
            .strip()
        )

        # Map the input to a valid court name
        court_name = COURT_ALIASES.get(court_name_input)

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


# --- Construct Update Message with Booking Links ---
def construct_update_message(player_name: str, slots_df) -> str:
    message = f"Hi {player_name}, here are the latest updates for your preferences:\n\n"
    
    for _, slot in slots_df.iterrows():
        business = slot['Business']
        sport = slot['Sport'].capitalize()
        locality = slot['Locality'].capitalize()
        timing = slot['Timing']
        booking_link = BUSINESS_LINKS.get(business, "Booking link not available")

        message += (
            f"• *Business*: {business} | *Sport*: {sport} | "
            f"*Locality*: {locality} | *Timing*: {timing}\n"
            f"👉 *Book Now*: {booking_link}\n\n"
        )

    return message
