import logging
from notifications.whatsapp_notifier import send_whatsapp_message
logger = logging.getLogger(__name__)

def handle_help_command(phone_number: str) -> None:
    try:
        # Comprehensive Help Message
        message = (
            "📋 *Available Commands:*\n\n"
            
            "*1. Preferences Management*\n"
            "✅ *Add a Sport*\n"
            "👉 Example: *add football*\n"
            "➔ Adds a new sport to your preferences.\n\n"
            
            "✅ *Remove a Sport*\n"
            "👉 Example: *remove pickleball*\n"
            "➔ Removes a sport from your preferences.\n\n"
            
            "✅ *View Current Preferences*\n"
            "👉 Example: *view preferences*\n"
            "➔ Shows your currently saved sports, notification time, and notification frequency.\n\n"
            
            "*2. Notifications Management*\n"
            "✅ *Change Notification Timing*\n"
            "👉 Example: *change notification timing to 9:00 AM*\n"
            "➔ Updates your preferred notification time.\n\n"
            
            "✅ *Change Notification Frequency*\n"
            "👉 Example: *change notification frequency to twice a week*\n"
            "➔ Updates how often you receive notifications.\n\n"
            
            "✅ *Supported Frequencies:*\n"
            "- *Daily:* Every day\n"
            "- *Weekly:* Every Monday\n"
            "- *Twice a Week:* Tuesdays & Thursdays\n"
            "- *Thrice a Week:* Mondays, Wednesdays & Fridays\n"
            "- *Weekends:* Saturdays & Sundays\n\n"
            
            "*3. Booking Updates*\n"
            "👉 Receive automatic notifications based on your preferences when courts become available.\n"
            "✅ *No action required!* We’ll notify you when a match is found.\n\n"
            
            "*4. General Commands*\n"
            "✅ *update*: Get notifications based on your preferences immediately.\n"
            "✅ *help*: Show this help message.\n"
            "✅ *discontinue*: Unsubscribe from updates.\n"
            "✅ *change sports from [old sports] to [new sports]*: Update sports preferences.\n"
            "✅ *updates on [court name]*: Get court-specific updates (e.g., *updates on TurfXL*).\n\n"
            
            "⚽🏏🎾 *Stay Active & Book Your Courts!*"
        )

        # Send the help message to the user
        send_whatsapp_message(phone_number, message)
        logger.info(f"Sent help message to {phone_number}")

    except Exception as e:
        logger.error(f"Error handling help command for {phone_number}: {e}")
