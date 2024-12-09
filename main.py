from flask import Flask, jsonify, request
from scheduler.job_scheduler import schedule_job
from sheets.player_data import process_player_notifications
import logging
from scheduler.scheduler_service import scheduler
from datetime import datetime, timedelta
from commands.command_processor import process_command 
# Initialize Flask App
app = Flask(__name__)

# Initialize Logger 
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Schedule Endpoint
@app.route("/schedule", methods=["GET"])
def schedule():

    try:
        logger.info("Fetching player notifications from Google Sheets...")
        
        # Directly fetch and process notifications
        process_player_notifications()

        return {"status": "notifications scheduled"}, 200

    except Exception as e:
        logger.error(f"Error scheduling notifications: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/twilio-webhook', methods=['POST'])
def twilio_webhook():
    """
    Handle incoming WhatsApp messages from Twilio.
    """
    try:
        incoming_message = request.form.get("Body")
        phone_number = request.form.get("From").replace("whatsapp:", "")

        logger.info(f"Message from {phone_number}: {incoming_message}")
        process_command(phone_number, incoming_message)

        return "OK", 200
    except Exception as e:
        logger.error(f"Error in /twilio-webhook: {e}")
        return "Internal Server Error", 500
# Health Check Endpoint
@app.route("/", methods=["GET"])
def index():
    return {"status": "running"}, 200

@app.route("/test-schedule", methods=["POST"])
def test_schedule():
    from scheduler.notification_scheduler import _notify_player

    try:
        player = {
            "Player Name": "Test User",
            "Phone Number": "+919903074027",
        }
        job_id = "test_notification"
        scheduler.add_job(
            func=_notify_player,
            trigger="date",
            run_date=datetime.utcnow() + timedelta(seconds=60),
            id=job_id,
            args=[player, "Test notification from Flask!"],
            replace_existing=True,
        )
        logger.info(f"Scheduled test job {job_id}.")
        return {"status": "job scheduled", "job_id": job_id}, 200

    except Exception as e:
        logger.error(f"Error scheduling test job: {e}")
        return {"status": "error", "message": str(e)}, 500

# Initialize Scheduler
@app.before_request
def init_notifications():
    logger.info("Initializing notifications...")
    process_player_notifications()

# Start Flask App
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True, use_reloader=False)
