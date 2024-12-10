from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def parse_time(time_str: str):
    try:
        if ":" in time_str:
            # Try 12-hour format first
            try:
                parsed_time = datetime.strptime(time_str.strip().lower(), "%I:%M %p")
            except ValueError:
                # Fallback to 24-hour format
                parsed_time = datetime.strptime(time_str.strip(), "%H:%M")
            return parsed_time.hour, parsed_time.minute
        else:
            raise ValueError("Invalid time format. Ensure the time is in HH:MM or HH:MM AM/PM format.")
    except Exception as e:
        logger.error(f"Error parsing time '{time_str}': {e}")
        raise ValueError(f"Invalid time format: {time_str}")
