"""Atomic shared fixed-window limits, persisted independently of request transactions."""
import hashlib
import time
from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from ..models.session import RateBucket

def enforce_limit(db, key: str, limit: int, seconds: int = 60):
    now = int(time.time())
    window = now // seconds * seconds
    digest = hashlib.sha256(f"{seconds}:{key}".encode()).hexdigest()
    try:
        with db.begin_nested():
            db.add(RateBucket(key=digest, window=window, count=0))
            db.flush()
    except IntegrityError:
        pass
    changed = db.execute(update(RateBucket).where(RateBucket.key == digest,
        RateBucket.window == window, RateBucket.count < limit).values(count=RateBucket.count + 1)).rowcount
    db.query(RateBucket).filter(RateBucket.window < now - 86400).delete()
    db.commit()
    if not changed:
        raise HTTPException(429, "Too many requests. Please try again shortly.", headers={"Retry-After": str(seconds - now % seconds)})
