import re

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
    remove_match = re.search(r"remove ([a-z, and]+)", command)

    if remove_match:
        sports_to_remove_raw = remove_match.group(1)
        sports_to_remove = re.split(r",| and | or ", sports_to_remove_raw)
        return {
            "action": "remove",
            "remove": [s.strip().capitalize() for s in sports_to_remove if s.strip()],
        }

    return {}