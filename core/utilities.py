import datetime

# Maps the admin transaction-filter range keys to a number of days.
_RANGE_DAYS = {"day": 1, "week": 7, "month": 30}


def since_from_range(range_key):
    """Return `now - N days` for range_key in {day, week, month}, else None (no date filter)."""
    days = _RANGE_DAYS.get(range_key)
    if not days:
        return None
    return datetime.datetime.now() - datetime.timedelta(days=days)