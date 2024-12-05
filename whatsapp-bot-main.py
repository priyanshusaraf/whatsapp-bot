from flask import Flask, request, jsonify
import gspread
from google.oauth2.service_account import Credentials
from twilio.rest import Client
import pandas as pd
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import os
import logging

# Load environment variables
load_dotenv()

# Validate environment variables
required_env_vars = ["GOOGLE_SHEETS_CREDENTIALS", "TWILIO_SID", "TWILIO_AUTH_TOKEN", "TWILIO_SANDBOX_NUMBER"]
for var in required_env_vars:
    if not os.getenv(var):
        raise EnvironmentError(f"Missing required environment variable: {var}")

# Flask App
app = Flask(__name__)

# Google Sheets Configuration
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
if not os.path.exists(SERVICE_ACCOUNT_FILE):
    raise FileNotFoundError(f"Service account file not found: {SERVICE_ACCOUNT_FILE}")

credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gspread_client = gspread.authorize(credentials)

# Twilio Configuration
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_SANDBOX_NUMBER = os.getenv("TWILIO_SANDBOX_NUMBER")
twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

# Logging Configuration
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Initialize APScheduler
scheduler = BackgroundScheduler()
scheduler.start()

# Frequency to days mapping
FREQUENCY_TO_DAYS = {
    "daily": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "weekly": ["Monday"],
    "twice a week": ["Tuesday", "Thursday"],
    "thrice a week": ["Monday", "Wednesday", "Friday"],
}

def map_frequency_to_days(frequency: str) -> list:
    """
    Map notification frequency to specific days of the week.
    """
    return FREQUENCY_TO_DAYS.get(frequency.lower(), [])

def parse_time(time_str: str) -> tuple:
    """
    Parse time in 'hh:mm AM/PM' format and return hour and minute.
    """
    try:
        time_obj = datetime.strptime(time_str.strip(), "%I:%M %p")
        return time_obj.hour, time_obj.minute
    except ValueError:
        raise ValueError(f"Invalid time format: {time_str}. Expected 'hh:mm AM/PM'.")

def send_scheduled_notification(player: pd.Series):
    """
    Send a scheduled notification for a player.
    """
    try:
        matched_slots = match_player_with_slots(player)
        if not matched_slots.empty:
            message = construct_business_message(player["Player Name"], matched_slots)
            send_whatsapp_message(player["Phone Number"], message)
        else:
            send_whatsapp_message(
                player["Phone Number"],
                f"Hi {player['Player Name']}, no available slots match your preferences right now."
            )
        logger.info(f"Notification sent to {player['Player Name']}.")
    except Exception as e:
        logger.error(f"Error sending scheduled notification for {player['Player Name']}: {e}")

def schedule_notifications():
    """Schedule notifications based on player preferences."""
    try:
        players_df = fetch_sheet_data("player-response-sheet", "Players")
        logger.info(f"Fetched players data for scheduling:\n{players_df}")

        # Map full weekday names to abbreviated names
        day_map = {
            "monday": "mon",
            "tuesday": "tue",
            "wednesday": "wed",
            "thursday": "thu",
            "friday": "fri",
            "saturday": "sat",
            "sunday": "sun"
        }

        # Iterate through each player and schedule notifications
        for _, player in players_df.iterrows():
            notification_frequency = player["Notification Frequency"].strip().lower()
            notification_time = player["Notification Time"].strip()

            # Normalize the day names based on frequency
            if notification_frequency == "daily":
                days = list(day_map.values())  # All days
            elif notification_frequency == "weekly":
                days = ["mon"]  # Default to Monday
            elif notification_frequency == "twice a week":
                days = ["mon", "thu"]
            elif notification_frequency == "thrice a week":
                days = ["mon", "wed", "fri"]
            else:
                logger.error(f"Unknown frequency: {notification_frequency} for player {player['Player Name']}")
                continue

            # Schedule notifications for each day
            for day in days:
                if day not in day_map.values():
                    logger.error(f"Invalid weekday abbreviation: {day}")
                    continue

                hour, minute = parse_time(notification_time)

                scheduler.add_job(
                    func=notify_player,
                    trigger="cron",
                    day_of_week=day,
                    hour=hour,
                    minute=minute,
                    args=[player],
                    id=f"{player['Phone Number']}_{day}",
                    replace_existing=True
                )
                logger.info(f"Scheduled notification for {player['Player Name']} on {day} at {notification_time}")
    except Exception as e:
        logger.error(f"Error scheduling notifications: {e}")


def parse_time(notification_time: str) -> tuple:
    """Parse time from string format like '10:00 AM' to hour and minute."""
    try:
        time, meridian = notification_time.split()
        hour, minute = map(int, time.split(":"))
        if meridian.lower() == "pm" and hour != 12:
            hour += 12
        if meridian.lower() == "am" and hour == 12:
            hour = 0
        return hour, minute
    except Exception as e:
        logger.error(f"Error parsing time '{notification_time}': {e}")
        raise ValueError(f"Invalid time format: {notification_time}")

# Helper Functions
def fetch_sheet_data(workspace_name: str, worksheet_name: str) -> pd.DataFrame:
    """Fetch data from a specified Google Sheets worksheet."""
    try:
        spreadsheet = gspread_client.open(workspace_name)
        worksheet = spreadsheet.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        logger.info(f"Fetched data from {workspace_name}/{worksheet_name}: {data}")
        return pd.DataFrame(data)
    except Exception as e:
        logger.error(f"Error fetching sheet data from {workspace_name}/{worksheet_name}: {e}")
        return pd.DataFrame()

def fetch_not_booked_slots() -> pd.DataFrame:
    """Fetch 'not booked' slots from all business sheets."""
    try:
        spreadsheet = gspread_client.open("business-workspace")
        all_business_data = []

        for sheet in spreadsheet.worksheets():
            logger.info(f"Processing sheet: {sheet.title}")
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            logger.info(f"Raw data fetched from sheet {sheet.title}:\n{df}")

            # Check for column names
            logger.info(f"Columns in sheet {sheet.title}: {df.columns.tolist()}")

            # Normalize fields
            if "Locality" in df.columns and "Sport" in df.columns and "Status" in df.columns:
                df["Locality"] = df["Locality"].str.strip().str.lower()
                df["Sport"] = df["Sport"].str.strip().str.lower()
                df["Status"] = df["Status"].str.strip().str.lower()

                # Filter for "not booked" slots
                not_booked = df[df["Status"] == "not booked"].copy()  # Avoid chained assignment
                not_booked.loc[:, "Business"] = sheet.title  # Add the business name

                all_business_data.append(not_booked)
            else:
                logger.error(f"Missing required columns in sheet {sheet.title}. Skipping this sheet.")

        if all_business_data:
            all_slots = pd.concat(all_business_data, ignore_index=True)
            logger.info(f"Fetched 'not booked' slots:\n{all_slots}")
            return all_slots
        else:
            logger.warning("No 'not booked' slots found in any sheet.")
            return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error fetching business data: {e}")
        return pd.DataFrame()

def match_player_with_slots(player: pd.Series) -> pd.DataFrame:
    """Find matching 'not booked' slots for a player's preferences."""
    try:
        all_slots = fetch_not_booked_slots()
        if all_slots.empty:
            logger.warning("No available slots fetched from business sheets.")
            return pd.DataFrame()

        # Normalize player preferences
        player_localities = [loc.strip().lower() for loc in player["Locality"].split(",")]
        player_preferences = [sport.strip().lower() for sport in player["Preferences"].split(",")]

        # Log player preferences and all slots
        logger.info(f"Player Localities: {player_localities}")
        logger.info(f"Player Preferences: {player_preferences}")
        logger.info(f"Fetched slots for matching:\n{all_slots}")

        # Filter for matching slots
        matched_slots = all_slots[
            (all_slots["Locality"].isin(player_localities)) &
            (all_slots["Sport"].isin(player_preferences))
        ]

        logger.info(f"Matched slots for player {player['Player Name']}:\n{matched_slots}")
        return matched_slots
    except Exception as e:
        logger.error(f"Error matching player {player['Player Name']} with slots: {e}")
        return pd.DataFrame()

def send_whatsapp_message(to: str, message: str) -> None:
    """Send a WhatsApp message using Twilio with retry."""
    try:
        twilio_client.messages.create(
            from_=TWILIO_SANDBOX_NUMBER,
            body=message,
            to=f"whatsapp:{to}"
        )
        logger.info(f"Message sent to {to}")
    except Exception as e:
        logger.error(f"Error sending WhatsApp message to {to}: {e}")
        # Retry once
        try:
            logger.info(f"Retrying to send message to {to}")
            twilio_client.messages.create(
                from_=TWILIO_SANDBOX_NUMBER,
                body=message,
                to=f"whatsapp:{to}"
            )
            logger.info(f"Message sent to {to} on retry")
        except Exception as retry_error:
            logger.error(f"Retry failed for {to}: {retry_error}")

def construct_business_message(player_name: str, matched_slots: pd.DataFrame) -> str:
    """Construct a message with business updates for the player."""
    if matched_slots.empty:
        return f"Hi {player_name}, no updates are currently available for your preferences."

    message = f"Hi {player_name}, here are your latest updates:\n\n"
    for _, slot in matched_slots.iterrows():
        message += f"- {slot['Business']} ({slot['Sport']}): {slot['Locality']}, {slot['Timing']}\n"
    return message

def notify_player(player: pd.Series) -> None:
    """Send notifications to a player about matching slots."""
    try:
        matched_slots = match_player_with_slots(player)

        # Log matched slots
        if not matched_slots.empty:
            logger.info(f"Matched slots for player {player['Player Name']}:\n{matched_slots}")
            message = construct_business_message(player["Player Name"], matched_slots)
            send_whatsapp_message(player["Phone Number"], message)
        else:
            logger.info(f"No slots matched for player {player['Player Name']}")
            send_whatsapp_message(
                player["Phone Number"],
                f"Hi {player['Player Name']}, no available slots match your preferences right now."
            )
    except Exception as e:
        logger.error(f"Error notifying player {player['Player Name']}: {e}")

# Routes
@app.route('/twilio-webhook', methods=['POST'])
def twilio_webhook():
    """Handle incoming WhatsApp messages via Twilio webhook."""
    try:
        incoming_message = request.form.get("Body")
        phone_number = request.form.get("From").replace("whatsapp:", "")

        logger.info(f"Message from {phone_number}: {incoming_message}")

        process_user_command(phone_number, incoming_message)
        return "OK", 200
    except Exception as e:
        logger.error(f"Error in /twilio-webhook: {e}")
        return "Internal Server Error", 500

@app.route('/')
def index():
    """Health check route."""
    return jsonify({"status": "running"}), 200

def process_user_command(phone_number: str, command: str) -> None:
    """Process commands from the user."""
    try:
        players_df = fetch_sheet_data("player-response-sheet", "Players")

        # Normalize phone numbers in Players sheet
        players_df["Phone Number"] = players_df["Phone Number"].apply(
            lambda x: f"+91{str(x).strip()}" if not str(x).startswith("+") else str(x).strip()
        )

        # Match normalized phone number
        player = players_df[players_df["Phone Number"] == phone_number]

        if player.empty:
            send_whatsapp_message(phone_number, "You are not registered. Please contact support.")
            return

        player = player.iloc[0]

        if command.lower() == "discontinue":
            send_whatsapp_message(phone_number, "You have been unsubscribed from updates.")
        elif command.lower() in ["update", "updates"]:
            notify_player(player)
        else:
            send_whatsapp_message(phone_number, "Invalid command. Please try again.")
    except Exception as e:
        logger.error(f"Error processing command for {phone_number}: {e}")

# Run the app
if __name__ == "__main__":
    schedule_notifications()
    app.run(host="0.0.0.0", port=8000, debug=True)
