import datetime
import os
import uuid

from core.settings import settings

# Maps the admin transaction-filter range keys to a number of days.
_RANGE_DAYS = {"day": 1, "week": 7, "month": 30}


def since_from_range(range_key):
    """Return `now - N days` for range_key in {day, week, month}, else None (no date filter)."""
    days = _RANGE_DAYS.get(range_key)
    if not days:
        return None
    return datetime.datetime.now() - datetime.timedelta(days=days)


def save_receipt_proof(data: bytes, ext: str = "jpg") -> str:
    """Write receipt proof bytes under <MEDIA_ROOT>/receipts/ and return the media-relative path.

    The returned path (e.g. "receipts/<uuid>.jpg") is stored on Receipt.proof_path and is
    served at /media/<path> (see core/app.py).
    """
    rel_dir = "receipts"
    abs_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)
    ext = (ext or "jpg").lstrip(".")
    name = f"{uuid.uuid4().hex}.{ext}"
    rel_path = f"{rel_dir}/{name}"
    with open(os.path.join(settings.MEDIA_ROOT, rel_path), "wb") as f:
        f.write(data)
    return rel_path