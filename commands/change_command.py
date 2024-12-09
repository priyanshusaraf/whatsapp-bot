import logging
from sheets.google_sheets import fetch_sheet_data, update_google_sheet
from commands.message_parser import parse_change_command
from notifications.whatsapp_notifier import send_whatsapp_message

logger = logging.getLogger(__name__)

# --- Handle Change Command ---
def handle_change_command(phone_number: str, command_text: str) -> None:
    try:
        # Fetch player data
        players_df = fetch_sheet_data("player-response-sheet", "Players")
        players_df["Phone Number"] = players_df["Phone Number"].apply(str).str.strip()
        player = players_df[players_df["Phone Number"] == phone_number]

        if player.empty:
            send_whatsapp_message(
                phone_number, "You are not registered. Please contact support."
            )
            return

        # Extract player's row index in Google Sheets
        player_data = player.iloc[0]
        row_index = player.index[0] + 2  # Adjust for header

        # Parse the change command
        updates = parse_change_command(command_text)
        if not updates:
            send_whatsapp_message(
                phone_number,
                "Invalid command. Use the format:\n"
                "- *add pickleball*\n"
                "- *change sports from pickleball and football to cricket*\n"
                "- *change notification timings from 10 am to 11 am*\n"
                "- *change notification day from Monday to Tuesday and Friday*"
            )
            return

        acknowledgment = []

        # --- Handle Add Command ---
        if "sports" in updates and updates["sports"]["action"] == "add":
            current_preferences = set(player_data["Preferences"].split(", "))
            new_preferences = set(updates["sports"]["new"])

            # Check if new sports already exist
            if not new_preferences - current_preferences:
                send_whatsapp_message(
                    phone_number,
                    f"Your sports preferences already include: {', '.join(new_preferences)}."
                )
                return

            # Update Google Sheets
            updated_preferences = list(current_preferences | new_preferences)
            update_google_sheet("Preferences", ", ".join(updated_preferences), row_index)
            acknowledgment.append(
                f"Added new sports to your preferences: {', '.join(new_preferences)}. "
                f"Your updated preferences are: {', '.join(updated_preferences)}."
            )

        # Send acknowledgment
        if acknowledgment:
            send_whatsapp_message(
                phone_number, "Your updates have been successfully processed:\n" + "\n".join(acknowledgment)
            )

    except Exception as e:
        logger.error(f"Error handling change command for {phone_number}: {e}")
        send_whatsapp_message(
            phone_number, "An error occurred while processing your request. Please try again later."
        )




logger = logging.getLogger(__name__)

def handle_add_command(phone_number: str, result: dict) -> None:
    try:
        # Fetch player data from Google Sheets
        players_df = fetch_sheet_data("player-response-sheet", "Players")
        players_df["Phone Number"] = players_df["Phone Number"].apply(str).str.strip()
        player = players_df[players_df["Phone Number"] == phone_number]

        if player.empty:
            send_whatsapp_message(
                phone_number, "You are not registered. Please contact support."
            )
            return

        # Extract the player's row index
        player_data = player.iloc[0]
        row_index = player.index[0] + 2  # Adjust for 1-based index (header)

        # Extract current preferences
        current_sports = player_data["Preferences"].split(", ")

        # Add New Sports
        new_sports = list(set(current_sports + result["new"]))
        update_google_sheet("Preferences", ", ".join(new_sports), row_index)

        send_whatsapp_message(
            phone_number,
            f"Added new sports: {', '.join(result['new'])}. Your updated preferences are: {', '.join(new_sports)}."
        )

    except Exception as e:
        logger.error(f"Error handling 'add' command for {phone_number}: {e}")
        send_whatsapp_message(
            phone_number, "An error occurred while processing your request. Please try again later."
        )
