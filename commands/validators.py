VALID_SPORTS = ["cricket", "football", "pickleball", "padel"]

def validate_sports(sports_list: list[str]) -> tuple[list[str], list[str]]:
    valid_sports = [sport.capitalize() for sport in sports_list if sport.lower() in VALID_SPORTS]
    invalid_sports = [sport.capitalize() for sport in sports_list if sport.lower() not in VALID_SPORTS]
    return valid_sports, invalid_sports
