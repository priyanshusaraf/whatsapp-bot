import logging
from sheets.google_sheets import fetch_sheet_data, update_google_sheet
from commands.message_parser import parse_change_command
from commands.validators import validate_sports
from notifications.whatsapp_notifier import send_whatsapp_message
import re
logger = logging.getLogger(__name__)

SUPPORTED_SPORTS = {
    'padel',
    'pickleball',
    'football',
    'cricket'
}

SUPPORTED_FREQUENCIES = {
    "daily": "Daily",
    "weekly": "Weekly",
    "twice a week": "Twice a Week",
    "thrice a week": "Thrice a Week",
    "weekend": "Weekend",
    "weekends": "Weekend",
}

# --- Handle Change Command ---
def handle_change_command(phone_number: str, command_text: str) -> None:
    try:
        # Normalize input
        command_text_lower = command_text.lower().strip()

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

        # --- Handle Notification Frequency Update ---
        if command_text_lower.startswith("change notification frequency to"):
            new_frequency = command_text_lower.replace(
                "change notification frequency to", ""
            ).strip()

            if new_frequency not in SUPPORTED_FREQUENCIES:
                send_whatsapp_message(
                    phone_number,
                    f"Invalid notification frequency. Supported values are: {', '.join(SUPPORTED_FREQUENCIES.values())}.",
                )
                return

            # Update the notification frequency
            update_google_sheet(
                "Notification Frequency", SUPPORTED_FREQUENCIES[new_frequency], row_index
            )
            send_whatsapp_message(
                phone_number,
                f"Your notification frequency has been updated to {SUPPORTED_FREQUENCIES[new_frequency]}.",
            )
            return  # Early exit after successful update

        # --- Handle Notification Timing Update ---
        if command_text_lower.startswith("change notification timing to"):
            new_time = command_text_lower.replace(
                "change notification timing to", ""
            ).strip()

            if not is_valid_time_format(new_time):
                send_whatsapp_message(
                    phone_number,
                    "Invalid time format. Use formats like *10:00 AM*, *10am*, *10:00am*, *10 AM*, etc.",
                )
                return

            # Update the notification time
            update_google_sheet("Notification Time", new_time, row_index)
            send_whatsapp_message(
                phone_number, f"Your notification time has been updated to {new_time}."
            )
            return  # Early exit after successful update

        # --- Handle Sports Update ---
        updates = parse_change_command(command_text_lower)
        if not updates:
            send_invalid_command_message(phone_number)
            return

        acknowledgment = []

        if "sports" in updates:
            sports_update = updates["sports"]
            current_preferences = set(player_data["Preferences"].split(", "))

            if sports_update["action"] == "add":
                new_sports = set(sports_update["new"]) & SUPPORTED_SPORTS
                invalid_sports = set(sports_update["new"]) - SUPPORTED_SPORTS

                added_sports = new_sports - current_preferences
                already_added = new_sports & current_preferences

                if added_sports:
                    updated_preferences = list(current_preferences | added_sports)
                    update_google_sheet(
                        "Preferences", ", ".join(updated_preferences), row_index
                    )
                    acknowledgment.append(
                        f"Added new sports: {', '.join(added_sports)}. "
                        f"Your updated preferences are: {', '.join(updated_preferences)}."
                    )

                if already_added:
                    acknowledgment.append(
                        f"The following sports were already in your preferences: {', '.join(already_added)}."
                    )

                if invalid_sports:
                    acknowledgment.append(
                        f"The following sports are not supported: {', '.join(invalid_sports)}."
                    )

            elif sports_update["action"] == "replace":
                valid_sports = set(sports_update["new"]) & SUPPORTED_SPORTS
                invalid_sports = set(sports_update["new"]) - SUPPORTED_SPORTS

                if valid_sports:
                    update_google_sheet(
                        "Preferences", ", ".join(valid_sports), row_index
                    )
                    acknowledgment.append(
                        f"Your sports preferences have been updated to {', '.join(valid_sports)}."
                    )

                if invalid_sports:
                    acknowledgment.append(
                        f"The following sports are not supported: {', '.join(invalid_sports)}."
                    )

        if acknowledgment:
            send_whatsapp_message(
                phone_number,
                "Your updates have been successfully processed:\n"
                + "\n".join(acknowledgment),
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


# --- Validate Time Format ---
def is_valid_time_format(time_str: str) -> bool:
    import re
    pattern = re.compile(r"^(0?[1-9]|1[0-2]):?[0-5][0-9]?\s?(am|pm|AM|PM)?$")
    return bool(pattern.match(time_str.strip()))


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

def is_valid_time_format(time_str: str) -> bool:
    """
    Validate common time formats like:
    - 10:00 AM
    - 10am
    - 10:00am
    - 10 AM
    """
    pattern = re.compile(r"^(0?[1-9]|1[0-2]):?[0-5]?[0-9]?\s?(am|pm|AM|PM)?$")
    return bool(pattern.match(time_str.strip()))



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