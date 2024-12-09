from twilio.rest import Client
from config.environment import TWILIO_SID, TWILIO_AUTH_TOKEN
from dotenv import load_dotenv
import os 


load_dotenv()
# Initialize Twilio Client
twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
TWILIO_SANDBOX_NUMBER = os.getenv('TWILIO_SANDBOX_NUMBER')