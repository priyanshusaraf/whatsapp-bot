import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Required Environment Variables
REQUIRED_ENV_VARS = [
    "GOOGLE_SHEETS_CREDENTIALS", 
    "TWILIO_SID", 
    "TWILIO_AUTH_TOKEN", 
    "TWILIO_SANDBOX_NUMBER"
]

# Validate environment variables
for var in REQUIRED_ENV_VARS:
    if not os.getenv(var):
        raise EnvironmentError(f"Missing required environment variable: {var}")

# Exported Environment Variables
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_SANDBOX_NUMBER = os.getenv("TWILIO_SANDBOX_NUMBER")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
