"""Deterministic time-expression normalisation (docs/adr/0003, docs/adr/0005).

`read(expression, observed_at, direction)` turns a phrase quoted from the source ("June 2025", "since
2023", "last week") into a window [earliest, latest) and a precision. It never guesses: anything it does
not recognise returns None, and the caller keeps that boundary UNKNOWN.

A month (or day and month) without a year needs a direction: "past" takes the most recent such date not
after the observation, "future" the next one not before it. `direction(text, position)` reads that from the
sentence (tense and scheduling words). Without linguistic evidence the direction is None and the phrase is
left unread, except when it names the observation's own month. The chosen year is always reported.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

MONTHS = {name: i + 1 for i, name in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
     "november", "december"])}
MONTHS.update({name[:3]: i for name, i in list(MONTHS.items())})
MONTHS["sept"] = 9

WEEKDAYS = {name: i for i, names in enumerate((("monday", "mon"), ("tuesday", "tue", "tues"), ("wednesday", "wed", "weds"),
                                                ("thursday", "thu", "thur", "thurs"), ("friday", "fri"), ("saturday", "sat"),
                                                ("sunday", "sun"))) for name in names}
LEADING = re.compile(r"^(?:in|on|since|from|until|till|til|to|by|as of|during|starting|ending|at)\s+")
ORDINAL = re.compile(r"(\d{1,2})(?:st|nd|rd|th)\b")
PRECISION_RANK = {"instant": 0, "day": 1, "month": 2, "year": 3, "unknown": 4}


@dataclass(frozen=True)
class Reading:
    earliest: datetime
    latest: datetime
    precision: str            # "day", "month" or "year"
    assumption: str | None = None
    explicit: bool = True     # False when the date is derived from the observation date (no stated year, or relative)


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


def _year_for(month, observed_at, day=1, direction="past"):
    """The year of (month, day): the most recent not after the observation ("past"), or the next one not
    before it ("future")."""
    year = observed_at.year
    if direction == "past" and (month, day) > (observed_at.month, observed_at.day):
        year -= 1
    if direction == "future" and (month, day) < (observed_at.month, observed_at.day):
        year += 1
    return year


# Words that show whether a sentence talks about the past or the future. Scheduling words that end in "-ed"
# ("scheduled", "planned", "expected") point forward, so they are checked before the generic past tense.
# Strong future cues settle the direction. Weak ones (plans and expectations) only count when nothing in the
# sentence points to the past: "we had planned to finish in June" may be about a June already gone.
STRONG_FUTURE = re.compile(r"^(?:will|shall|'ll|going|due|deadline|upcoming|next)$")
WEAK_FUTURE = re.compile(
    r"^(?:scheduled|planned|plan|plans|expected|expect|expects|aim|aims|target|targets|targeted|intend|intends|"
    r"intended|forecast|forecasts)$")
PAST_CUES = re.compile(
    r"^(?:was|were|had|did|ago|last|previous|previously|earlier|already|since|\w+ed|"
    r"left|went|began|became|came|made|said|told|took|gave|got|met|ran|wrote|sent|spent|won|lost|held|"
    r"led|paid|sold|bought|brought|thought|found|kept|built|chose|set|quit|hired|fired|joined)$")
RESCHEDULED_TO = re.compile(
    r"\b(?:moved|pushed|postponed|rescheduled|delayed|slipped|brought forward|deferred)(?:\s+back)?\s+(?:to|until|into)\s*$", re.I)
WORD = re.compile(r"[a-z']+")
NOT_PAST = frozenset("need needed indeed speed seed feed bed red shed embed proceed exceed succeed".split()) - {"needed"}


def direction(text, position=None):
    """"past", "future" or None for a time phrase at `position` in `text`, from the nearest tense or
    scheduling word in the same sentence (words before the phrase first, then after). None when the
    sentence gives no evidence."""
    if position is None:
        position = 0
    start = max(text.rfind(c, 0, position) for c in ".!?\n") + 1
    ends = [i for i in (text.find(c, position) for c in ".!?\n") if i != -1]
    end = min(ends) if ends else len(text)
    before, after = text[start:position], text[position:end]
    if RESCHEDULED_TO.search(before):
        return "future"  # "postponed to June": the new date lies ahead
    nearby = list(reversed(WORD.findall(before.lower()))) + WORD.findall(after.lower())
    past_anywhere = any(_is_past(w) for w in nearby)
    for w in nearby:
        if STRONG_FUTURE.match(w):
            return "future"
        if _is_past(w):
            return "past"
        if WEAK_FUTURE.match(w):
            return None if past_anywhere else "future"  # mixed signals: not resolved
    return None


def _is_past(word):
    return bool(PAST_CUES.match(word)) and word not in NOT_PAST and not WEAK_FUTURE.match(word)


def read(expression, observed_at, direction=None):
    """See the module docstring. `direction` ("past", "future" or None) only matters for a month or day
    without a year."""
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
            y = _year_without_evidence(MONTHS[name], obs, direction, day)
            if y is None:
                return None
            r = _day(y, MONTHS[name], day)
            return r and Reading(r.earliest, r.latest, "day", _assumption(y, direction, MONTHS[name], obs), explicit=False)
    if text in MONTHS:
        y = _year_without_evidence(MONTHS[text], obs, direction)
        if y is None:
            return None
        return Reading(*_month_window(y, MONTHS[text]), "month", _assumption(y, direction, MONTHS[text], obs),
                       explicit=False)

    if text == "today":
        return Reading(today, today + timedelta(days=1), "day", explicit=False)
    if text == "yesterday":
        return Reading(today - timedelta(days=1), today, "day", explicit=False)
    if text in ("last week", "the previous week"):
        monday = today - timedelta(days=today.weekday())
        return Reading(monday - timedelta(days=7), monday, "day", explicit=False)
    if m := re.fullmatch(r"last ([a-z]+)", text):
        if m.group(1) in WEEKDAYS:
            return _last_weekday(WEEKDAYS[m.group(1)], today)
        if m.group(1) == "weekend":
            return _last_weekend(today)
    if text in ("this month",):
        return Reading(*_month_window(obs.year, obs.month), "month", explicit=False)
    if text in ("last month", "the previous month"):
        y, mo = (obs.year - 1, 12) if obs.month == 1 else (obs.year, obs.month - 1)
        return Reading(*_month_window(y, mo), "month", explicit=False)
    if text == "this year":
        return Reading(_utc(obs.year), _utc(obs.year + 1), "year", explicit=False)
    if text in ("last year", "the previous year"):
        return Reading(_utc(obs.year - 1), _utc(obs.year), "year", explicit=False)
    return None


def _settled(target, today):
    """"Last Friday" said on a Wednesday can only mean the most recent Friday. Said on a Saturday it could be yesterday or
    the Friday before, so it stays unread. Weeks start on Monday or Sunday depending on who is speaking, so the day must
    fall in the previous week under both."""
    return all((target + shift) % 7 >= (today.weekday() + shift) % 7 for shift in (0, 1))


def _last_weekday(target, today):
    if not _settled(target, today):
        return None
    start = today - timedelta(days=(today.weekday() - target - 1) % 7 + 1)
    return Reading(start, start + timedelta(days=1), "day", "the most recent such day before the observation", explicit=False)


def _last_weekend(today):
    """The Saturday and Sunday before this week. Said during a weekend it could mean this one, so it stays unread."""
    if today.weekday() >= 5:
        return None
    monday = today - timedelta(days=today.weekday())
    return Reading(monday - timedelta(days=2), monday, "day", "the weekend before the observation's week", explicit=False)


def _year_without_evidence(month, obs, direction, day=None):
    if direction in ("past", "future"):
        return _year_for(month, obs, day or 1, direction) if day else _year_for_month(month, obs, direction)
    if month == obs.month:
        return obs.year  # the observation's own month: the same in either direction
    return None


def _year_for_month(month, obs, direction):
    if direction == "past":
        return obs.year - (month > obs.month)
    return obs.year + (month < obs.month)


def _assumption(year, direction, month, obs):
    if direction in ("past", "future"):
        return f"year {year} inferred from the observation date ({direction} tense)"
    return f"year {year} inferred: the observation's own month"


def coarsest(*precisions):
    present = [p for p in precisions if p]
    return max(present, key=PRECISION_RANK.__getitem__) if present else None
