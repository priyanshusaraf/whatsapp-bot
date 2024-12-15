import re
from datetime import datetime, timedelta

COURT_ALIASES = {
    "turfxl": "TurfXL",
    "playplex": "PlayPlex",
    "turfedge": "TurfEdge",
    "padelclub": "The Padel Club",
}

def parse_change_command(command_text: str) -> dict:
    updates = {}
    command = command_text.lower().strip()

    # Handle Sports Change
    sports_change_match = re.search(
        r"change sports from ([a-z ,\-and]+) to ([a-z ,\-and]+)", command
    )
    if sports_change_match:
        old_sports = re.split(r",| and | or ", sports_change_match.group(1))
        new_sports = re.split(r",| and | or ", sports_change_match.group(2))
        updates["sports"] = {
            "action": "replace",
            "old": [s.strip().capitalize() for s in old_sports if s.strip()],
            "new": [s.strip().capitalize() for s in new_sports if s.strip()],
        }

    # Handle Sports Add
    sports_add_match = re.search(r"add ([a-z ,\-and]+)", command)
    if sports_add_match:
        additional_sports = re.split(r",| and | or ", sports_add_match.group(1))
        updates["sports"] = {
            "action": "add",
            "new": [s.strip().capitalize() for s in additional_sports if s.strip()],
        }

    # Handle Notification Timings
    timing_change_match = re.search(
        r"change notification timings from ([a-z0-9: ]+ ?[ap]m?) to ([a-z0-9: ]+ ?[ap]m?)",
        command,
    )
    if timing_change_match:
        updates["timing"] = {
            "old": timing_change_match.group(1).strip(),
            "new": timing_change_match.group(2).strip(),
        }

    # Handle Notification Days
    day_change_match = re.search(
        r"change notification day from ([a-z ,\-and]+) to ([a-z ,\-and]+)", command
    )
    if day_change_match:
        old_days = re.split(r",| and | or ", day_change_match.group(1))
        new_days = re.split(r",| and | or ", day_change_match.group(2))
        updates["days"] = {
            "old": [d.strip().capitalize() for d in old_days if d.strip()],
            "new": [d.strip().capitalize() for d in new_days if d.strip()],
        }

    return updates


def parse_add_command(command_text: str) -> dict:
    command = command_text.lower().strip()
    sports_add_match = re.search(r"add ([a-z ,\-and]+)", command)
    
    if sports_add_match:
        additional_sports = re.split(r",| and | or ", sports_add_match.group(1))
        return {
            "action": "add",
            "new": [s.strip().capitalize() for s in additional_sports if s.strip()],
        }
    return {}


def parse_remove_command(command_text: str) -> dict:
    command = command_text.lower().strip()
    remove_match = re.search(r"remove ([a-z ,\-and]+)", command)

    if remove_match:
        sports_to_remove_raw = remove_match.group(1)
        sports_to_remove = re.split(r",| and | or ", sports_to_remove_raw)
        return {
            "action": "remove",
            "remove": [s.strip().capitalize() for s in sports_to_remove if s.strip()],
        }

    return {}


def parse_court_name(command_text: str) -> str:
    """
    Parse court names from the command text, ignoring case and extra spaces.
    Returns the standardized court name if found, otherwise None.
    """
    command = re.sub(r"\s+", "", command_text.lower())  # Remove spaces and lowercase
    for alias, court_name in COURT_ALIASES.items():
        if alias in command:
            return court_name
    return None

def parse_timing(timing_text: str, output_format: str = "%H:%M") -> str:
    """
    Parse and format timing from the command text.
    Supports single-digit hours, missing minutes, and AM/PM.

    Args:
        timing_text (str): The timing string to parse.
        output_format (str): The desired time output format (default is 24-hour).

    Returns:
        str: The formatted time string or 'Invalid time format' if parsing fails.
    """
    try:
        now = datetime.now()
        timing_text = timing_text.strip().lower().replace(' ', '')

        # Handle single-digit hour inputs (e.g., "8" -> "8:00 AM/PM")
        if re.match(r"^\d{1,2}$", timing_text):
            hour = int(timing_text)
            if 1 <= hour <= 12:
                timing_text = f"{hour}:00am" if hour <= 7 else f"{hour}:00pm"
            else:
                raise ValueError("Hour out of range")

        # Handle hour:minute without AM/PM
        if re.match(r"^\d{1,2}:\d{2}$", timing_text):
            hour, minute = map(int, timing_text.split(":"))
            if 1 <= hour <= 12 and 0 <= minute <= 59:
                timing_text += "am" if hour <= 7 else "pm"

        # Parse and adjust time
        timing = datetime.strptime(timing_text, "%I:%M%p")
        timing = timing.replace(year=now.year, month=now.month, day=now.day)

        # Auto-adjust to the nearest future time
        if timing < now:
            timing += timedelta(hours=12)

        # Format as requested
        return timing.strftime(output_format)

    except ValueError:
        return "Invalid time format"
