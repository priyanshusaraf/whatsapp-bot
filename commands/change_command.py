import logging
from sheets.google_sheets import fetch_sheet_data, update_google_sheet
from commands.message_parser import parse_change_command
from commands.validators import validate_sports
from notifications.whatsapp_notifier import send_whatsapp_message

logger = logging.getLogger(__name__)

SUPPORTED_SPORTS = {
    'padel',
    'pickleball',
    'football',
    'cricket'
}

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
            send_invalid_command_message(phone_number)
            return

        acknowledgment = []

        # --- Handle Sports Update ---
        if "sports" in updates:
            sports_update = updates["sports"]
            valid_sports, invalid_sports = validate_sports(sports_update["new"])

            current_preferences = set(player_data["Preferences"].split(", "))

            if sports_update["action"] == "add":
                new_preferences = set(valid_sports) - current_preferences

                if new_preferences:
                    updated_preferences = list(current_preferences | new_preferences)
                    update_google_sheet("Preferences", ", ".join(updated_preferences), row_index)
                    acknowledgment.append(
                        f"Added new sports: {', '.join(new_preferences)}. "
                        f"Your updated preferences are: {', '.join(updated_preferences)}."
                    )
                else:
                    acknowledgment.append("No new sports were added as all were already in your preferences.")

            elif sports_update["action"] == "replace":
                if valid_sports:
                    update_google_sheet("Preferences", ", ".join(valid_sports), row_index)
                    acknowledgment.append(
                        f"Your sports preferences have been updated from "
                        f"{', '.join(player_data['Preferences'].split(', '))} to {', '.join(valid_sports)}."
                    )
                else:
                    acknowledgment.append("No valid sports were provided for replacement.")

            if invalid_sports:
                acknowledgment.append(
                    f"The following sports were not added as they are not supported: {', '.join(invalid_sports)}."
                )

        # --- Handle Timing Update ---
        if "timing" in updates:
            timing_update = updates["timing"]
            update_google_sheet("Notification Time", timing_update["new"], row_index)
            acknowledgment.append(
                f"Your notification timing has been updated from {timing_update['old']} to {timing_update['new']}."
            )

        # --- Handle Notification Days Update ---
        if "days" in updates:
            day_update = updates["days"]
            update_google_sheet("Notification Frequency", ", ".join(day_update["new"]), row_index)
            acknowledgment.append(
                f"Your notification days have been updated from {', '.join(day_update['old'])} to {', '.join(day_update['new'])}."
            )

        # Send acknowledgment if any updates were made
        if acknowledgment:
            send_whatsapp_message(
                phone_number, "Your updates have been successfully processed:\n" + "\n".join(acknowledgment)
            )
        else:
            send_whatsapp_message(
                phone_number, "No updates were made. Please check your command and try again."
            )

    except Exception as e:
        logger.error(f"Error handling change command for {phone_number}: {e}")
        send_whatsapp_message(
            phone_number, "An error occurred while processing your request. Please try again later."
        )


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
        row_index = player.index[0] + 2  # Adjust for header

        # Extract current preferences (normalized)
        current_sports = set(
            sport.strip().lower() for sport in player_data["Preferences"].split(", ")
        )

        # Normalize requested sports
        requested_sports = set(
            sport.strip().lower() for sport in result["new"]
        )

        logger.debug(f"Current sports: {current_sports}")
        logger.debug(f"Requested sports: {requested_sports}")

        # Validate sports against the supported list
        valid_sports = requested_sports & {sport.lower() for sport in SUPPORTED_SPORTS}
        invalid_sports = requested_sports - {sport.lower() for sport in SUPPORTED_SPORTS}
        new_sports_to_add = valid_sports - current_sports
        already_added_sports = valid_sports & current_sports

        logger.debug(f"Valid sports: {valid_sports}")
        logger.debug(f"Invalid sports: {invalid_sports}")
        logger.debug(f"New sports to add: {new_sports_to_add}")
        logger.debug(f"Already added sports: {already_added_sports}")

        # Prepare response messages
        response_parts = []

        if new_sports_to_add:
            updated_preferences = list(current_sports | new_sports_to_add)
            update_google_sheet(
                "Preferences",
                ", ".join(sport.capitalize() for sport in updated_preferences),
                row_index,
            )
            response_parts.append(
                f"Added new sports to your preferences: {', '.join(sport.capitalize() for sport in new_sports_to_add)}."
            )
            response_parts.append(
                f"Your updated preferences are: {', '.join(sport.capitalize() for sport in updated_preferences)}."
            )

        if already_added_sports:
            response_parts.append(
                f"The following sports were already in your preferences: {', '.join(sport.capitalize() for sport in already_added_sports)}."
            )

        if invalid_sports:
            response_parts.append(
                f"The following sports were not added as they are not supported: {', '.join(sport.capitalize() for sport in invalid_sports)}."
            )

        if not response_parts:
            response_parts.append("No changes were made to your preferences.")

        # Send the final response to the user
        send_whatsapp_message(phone_number, "\n".join(response_parts))

    except Exception as e:
        logger.error(f"Error handling 'add' command for {phone_number}: {e}")
        send_whatsapp_message(
            phone_number, "An error occurred while processing your request. Please try again later."
        )

# commands/change_command.py

import logging
from sheets.google_sheets import fetch_sheet_data, update_google_sheet
from commands.message_parser import parse_remove_command
from notifications.whatsapp_notifier import send_whatsapp_message

logger = logging.getLogger(__name__)

SUPPORTED_SPORTS = {"football", "cricket", "padel", "pickleball"}

def handle_remove_command(phone_number: str, result: dict) -> None:
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
        row_index = player.index[0] + 2  # Adjust for header

        # Extract current preferences
        current_sports = set(
            sport.strip().lower() for sport in player_data["Preferences"].split(", ")
        )

        # Extract requested sports to remove
        requested_sports = set(
            sport.strip().lower() for sport in result["remove"]
        )

        logger.debug(f"Current sports: {current_sports}")
        logger.debug(f"Requested sports to remove: {requested_sports}")

        # Validate sports
        valid_sports_to_remove = requested_sports & current_sports
        invalid_sports = requested_sports - SUPPORTED_SPORTS
        not_in_preferences = requested_sports - current_sports

        logger.debug(f"Valid sports to remove: {valid_sports_to_remove}")
        logger.debug(f"Invalid sports: {invalid_sports}")
        logger.debug(f"Not in preferences: {not_in_preferences}")

        # Prepare response messages
        response_parts = []

        if valid_sports_to_remove:
            updated_preferences = list(current_sports - valid_sports_to_remove)
            update_google_sheet(
                "Preferences",
                ", ".join(sport.capitalize() for sport in updated_preferences),
                row_index,
            )
            response_parts.append(
                f"Removed: {', '.join(sport.capitalize() for sport in valid_sports_to_remove)}."
            )
            response_parts.append(
                f"Your updated preferences are: {', '.join(sport.capitalize() for sport in updated_preferences)}."
            )

        if not_in_preferences and not valid_sports_to_remove:
            response_parts.append(
                f"The following sports were not in your preferences: {', '.join(sport.capitalize() for sport in not_in_preferences)}."
            )

        if invalid_sports:
            response_parts.append(
                f"The following sports are not supported: {', '.join(sport.capitalize() for sport in invalid_sports)}."
            )

        if not response_parts:
            response_parts.append("No changes were made to your preferences.")

        # Send the final response to the user
        send_whatsapp_message(phone_number, "\n".join(response_parts))

    except Exception as e:
        logger.error(f"Error handling 'remove' command for {phone_number}: {e}")
        send_whatsapp_message(
            phone_number, "An error occurred while processing your request. Please try again later."
        )



# --- Send Invalid Command Message ---
def send_invalid_command_message(phone_number: str) -> None:
    send_whatsapp_message(
        phone_number,
        "Invalid command. Use the format:\n"
        "- *add pickleball*\n"
        "- *change sports from pickleball and football to cricket*\n"
        "- *change notification timings from 10 am to 11 am*\n"
        "- *change notification day from Monday to Tuesday and Friday*"
    )


