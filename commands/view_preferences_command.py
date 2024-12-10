import logging
from notifications.whatsapp_notifier import send_whatsapp_message
from sheets.google_sheets import fetch_sheet_data

logger = logging.getLogger(__name__)

def handle_view_preferences_command(phone_number: str) -> None:
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

        # Extract player data
        player_data = player.iloc[0]

        preferences_message = (
            f"Your current preferences are:\n\n"
            f"• *Sports*: {player_data['Preferences']}\n"
            f"• *Notification Timing*: {player_data['Notification Time']}\n"
            f"• *Notification Frequency*: {player_data['Notification Frequency']}\n"
        )

        send_whatsapp_message(phone_number, preferences_message)

    except Exception as e:
        logger.error(f"Error handling view preferences command for {phone_number}: {e}")
        send_whatsapp_message(
            phone_number, 
            "An error occurred while processing your request. Please try again later."
        )
