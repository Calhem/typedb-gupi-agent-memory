"""Deterministic time-expression normalisation (docs/adr/0003, docs/adr/0005).

`read(expression, observed_at)` turns a phrase quoted from the source ("June 2025", "since 2023",
"last week") into a window [earliest, latest) and a precision. It never guesses: anything it does not
recognise returns None, and the caller keeps that boundary UNKNOWN. When it has to assume something
(a month without a year is the most recent such month not after the observation), it says so.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

MONTHS = {name: i + 1 for i, name in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
     "november", "december"])}
MONTHS.update({name[:3]: i for name, i in list(MONTHS.items())})
MONTHS["sept"] = 9

LEADING = re.compile(r"^(?:in|on|since|from|until|till|til|to|by|as of|during|starting|ending|at)\s+")
ORDINAL = re.compile(r"(\d{1,2})(?:st|nd|rd|th)\b")
PRECISION_RANK = {"instant": 0, "day": 1, "month": 2, "year": 3, "unknown": 4}


@dataclass(frozen=True)
class Reading:
    earliest: datetime
    latest: datetime
    precision: str            # "day", "month" or "year"
    assumption: str | None = None


def _utc(y, m=1, d=1):
    return datetime(y, m, d, tzinfo=timezone.utc)


def _month_window(y, m):
    return _utc(y, m), _utc(y + (m == 12), m % 12 + 1)


def _day(y, m, d):
    try:
        start = _utc(y, m, d)
    except ValueError:
        return None
    return Reading(start, start + timedelta(days=1), "day")


def _year_for(month, observed_at, day=1):
    """The most recent (month, day) not after the observation date."""
    year = observed_at.year
    if (month, day) > (observed_at.month, observed_at.day):
        year -= 1
    return year


def read(expression, observed_at):
    if not expression or observed_at is None:
        return None
    text = ORDINAL.sub(r"\1", expression.strip().lower().rstrip(".,;"))
    text = re.sub(r"\s+", " ", text.replace(",", " ")).strip()
    while LEADING.match(text):
        text = LEADING.sub("", text, count=1)
    obs = observed_at.astimezone(timezone.utc)
    today = _utc(obs.year, obs.month, obs.day)

    if m := re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", text):
        return _day(*map(int, m.groups()))
    if m := re.fullmatch(r"(\d{4})-(\d{2})", text):
        y, mo = map(int, m.groups())
        return Reading(*_month_window(y, mo), "month") if 1 <= mo <= 12 else None
    if m := re.fullmatch(r"(\d{1,2}) ([a-z]+) (\d{4})", text):
        if m.group(2) in MONTHS:
            return _day(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)))
    if m := re.fullmatch(r"([a-z]+) (\d{1,2}) (\d{4})", text):
        if m.group(1) in MONTHS:
            return _day(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2)))
    if m := re.fullmatch(r"([a-z]+) (\d{4})", text):
        if m.group(1) in MONTHS:
            return Reading(*_month_window(int(m.group(2)), MONTHS[m.group(1)]), "month")
    if m := re.fullmatch(r"(?:the year )?(\d{4})", text):
        y = int(m.group(1))
        return Reading(_utc(y), _utc(y + 1), "year") if 1900 <= y <= 2100 else None
    if (m := re.fullmatch(r"(\d{1,2}) ([a-z]+)", text)) or (m2 := re.fullmatch(r"([a-z]+) (\d{1,2})", text)):
        day, name = (int(m.group(1)), m.group(2)) if m else (int(m2.group(2)), m2.group(1))
        if name in MONTHS:
            y = _year_for(MONTHS[name], obs, day)
            r = _day(y, MONTHS[name], day)
            return r and Reading(r.earliest, r.latest, "day", f"year {y} inferred from the observation date")
    if text in MONTHS:
        y = _year_for(MONTHS[text], obs)
        return Reading(*_month_window(y, MONTHS[text]), "month", f"year {y} inferred from the observation date")

    if text == "today":
        return Reading(today, today + timedelta(days=1), "day")
    if text == "yesterday":
        return Reading(today - timedelta(days=1), today, "day")
    if text in ("last week", "the previous week"):
        monday = today - timedelta(days=today.weekday())
        return Reading(monday - timedelta(days=7), monday, "day")
    if text in ("this month",):
        return Reading(*_month_window(obs.year, obs.month), "month")
    if text in ("last month", "the previous month"):
        y, mo = (obs.year - 1, 12) if obs.month == 1 else (obs.year, obs.month - 1)
        return Reading(*_month_window(y, mo), "month")
    if text == "this year":
        return Reading(_utc(obs.year), _utc(obs.year + 1), "year")
    if text in ("last year", "the previous year"):
        return Reading(_utc(obs.year - 1), _utc(obs.year), "year")
    return None


def coarsest(*precisions):
    present = [p for p in precisions if p]
    return max(present, key=PRECISION_RANK.__getitem__) if present else None
