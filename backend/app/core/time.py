"""UTC at storage boundaries, compatible with the existing SQLite schema."""
from datetime import datetime, timezone


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso_utc(value):
    return value.replace(tzinfo=timezone.utc).isoformat() if value and value.tzinfo is None else value.isoformat() if value else None
