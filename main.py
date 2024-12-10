from flask import Flask, jsonify, request
from scheduler.scheduler_service import scheduler
from sheets.player_data import process_player_notifications
from commands.command_processor import process_command
import logging
from datetime import datetime, timedelta

# Initialize Flask App
app = Flask(__name__)

# Initialize Logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# --- Scheduler Initialization ---
def initialize_scheduler():
    """
    Initializes the scheduler, starts it if not running, and restores jobs.
    """
    try:
        if not scheduler.running:
            scheduler.start()
            logger.info("Scheduler started successfully.")
        else:
            logger.info("Scheduler already running.")

        logger.info("Restoring scheduled jobs from Google Sheets...")
        process_player_notifications()  # Restore jobs on startup

        # Print jobs for detailed review
        scheduled_jobs = scheduler.get_jobs()
        if scheduled_jobs:
            for job in scheduled_jobs:
                logger.info(f"Scheduled Job: {job.id} | Next Run: {job.next_run_time}")
        else:
            logger.warning("No jobs currently scheduled.")

        logger.info("Jobs successfully restored.")
    except Exception as e:
        logger.error(f"Error initializing scheduler: {e}")

# --- Health Check Endpoint ---
@app.route("/", methods=["GET"])
def index():
    """
    Health check endpoint to ensure the server is running.
    """
    return {"status": "running"}, 200

# --- Manual Schedule Endpoint ---
@app.route("/schedule", methods=["GET"])
def schedule():
    """
    Manually trigger job scheduling for notifications.
    """
    try:
        logger.info("Fetching player notifications from Google Sheets...")
        process_player_notifications()  # Manual scheduling trigger

        # Print scheduled jobs after processing
        scheduled_jobs = scheduler.get_jobs()
        if scheduled_jobs:
            logger.info("Updated scheduled jobs:")
            for job in scheduled_jobs:
                logger.info(f"Job: {job.id} | Next Run: {job.next_run_time}")
        else:
            logger.warning("No jobs scheduled after manual scheduling.")

        return {"status": "notifications scheduled"}, 200
    except Exception as e:
        logger.error(f"Error scheduling notifications: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# --- Webhook for Twilio WhatsApp Messages ---
# --- Webhook for Twilio WhatsApp Messages ---
@app.route("/twilio-webhook", methods=["POST"])
def twilio_webhook():
    """
    Handle incoming WhatsApp messages from Twilio.
    Reschedules jobs after every change command.
    """
    try:
        incoming_message = request.form.get("Body")
        phone_number = request.form.get("From").replace("whatsapp:", "")

        logger.info(f"Message from {phone_number}: {incoming_message}")
        
        # Process the command and update Google Sheets
        process_command(phone_number, incoming_message)

        # Fetch updated notifications from Google Sheets
        logger.info("Rescheduling notifications after preference update...")
        process_player_notifications()

        # Print updated jobs
        scheduled_jobs = scheduler.get_jobs()
        if scheduled_jobs:
            logger.info("Updated scheduled jobs after processing command:")
            for job in scheduled_jobs:
                logger.info(f"Job: {job.id} | Next Run: {job.next_run_time}")
        else:
            logger.warning("No jobs scheduled after processing command.")

        return "OK", 200
    except Exception as e:
        logger.error(f"Error in /twilio-webhook: {e}")
        return "Internal Server Error", 500

# --- Test Job Scheduling Endpoint ---
@app.route("/test-schedule", methods=["POST"])
def test_schedule():
    """
    Schedule a one-time test notification.
    """
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

        # Confirm job creation
        scheduled_jobs = scheduler.get_jobs()
        if scheduled_jobs:
            logger.info("Jobs after test scheduling:")
            for job in scheduled_jobs:
                logger.info(f"Job: {job.id} | Next Run: {job.next_run_time}")
        else:
            logger.warning("No jobs scheduled after test job creation.")

        return {"status": "job scheduled", "job_id": job_id}, 200
    except Exception as e:
        logger.error(f"Error scheduling test job: {e}")
        return {"status": "error", "message": str(e)}, 500

# --- Flask App Entry Point ---
if __name__ == "__main__":
    logger.info("Starting Flask app...")
    initialize_scheduler()  # Initialize scheduler and restore jobs
    app.run(host="0.0.0.0", port=8000, debug=True, use_reloader=False)
