from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def parse_time(notification_time: str) -> tuple:
    try:
        time_obj = datetime.strptime(notification_time.strip(), "%I:%M %p")
        return time_obj.hour, time_obj.minute
    except ValueError as e:
        logger.error(f"Error parsing time '{notification_time}': {e}")
        raise ValueError(f"Invalid time format: {notification_time}")