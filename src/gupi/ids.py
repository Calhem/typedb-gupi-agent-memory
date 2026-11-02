"""Stable identifiers: the same input always gives the same id, so re-ingesting finds what is already there."""

import hashlib
import json
from datetime import datetime, timezone


def _canonical(value):
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("datetimes in ids must be timezone-aware")
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, dict):
        return {str(k): _canonical(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    return value


def digest(*parts):
    text = json.dumps(_canonical(list(parts)), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable_id(prefix, *parts):
    return f"{prefix}:{digest(*parts)[:32]}"


def content_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
