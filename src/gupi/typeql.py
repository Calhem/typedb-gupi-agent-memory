"""Safe TypeQL construction.

Values never go into query text: they are passed as parameters through the driver's `given` stage
(`given $v: string; insert $x isa note, has text == $v;`). The only things written into query text are
type, role and attribute labels, and those must match LABEL and, where the caller checks, the live schema.
"""

import re
from datetime import date, datetime, timezone

from typedb.driver import Datetime

LABEL = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
VARIABLE = re.compile(r"^[a-z][a-z0-9_]*$")
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def label(name):
    """A type, role or attribute label, safe to place in query text."""
    if not isinstance(name, str) or not LABEL.match(name):
        raise ValueError(f"not a valid TypeQL label: {name!r}")
    return name


def value_type(value):
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "double"
    if isinstance(value, str):
        return "string"
    if isinstance(value, datetime):
        return "datetime-tz"
    if isinstance(value, date):
        return "date"
    raise TypeError(f"unsupported parameter type: {type(value).__name__}")


def to_driver(value):
    """Convert a Python value to what the driver accepts. Datetimes must be timezone-aware and go in as UTC."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("datetimes must be timezone-aware")
        delta = value.astimezone(timezone.utc) - EPOCH
        return Datetime.fromtimestamp(delta.days * 86400 + delta.seconds, delta.microseconds * 1000, offset_seconds=0)
    return value


def given(params):
    """The `given` header declaring each parameter's value type, e.g. `given $id: string, $at: datetime-tz;`."""
    if not params:
        return ""
    parts = []
    for name, value in params.items():
        if not VARIABLE.match(name):
            raise ValueError(f"not a valid parameter name: {name!r}")
        parts.append(f"${name}: {value_type(value)}")
    return "given " + ", ".join(parts) + ";\n"


def run(tx, body, params=None):
    """Run `body` with one row of parameters (a dict of name -> value) and return the resolved answer."""
    params = params or {}
    rows = [{k: to_driver(v) for k, v in params.items()}] if params else None
    return tx.query(given(params) + body, given_rows=rows).resolve()


def run_rows(tx, body, rows):
    """Run `body` once per parameter row in a single query (rows must share names and value types)."""
    rows = list(rows)
    if not rows:
        return None
    return tx.query(given(rows[0]) + body, given_rows=[{k: to_driver(v) for k, v in r.items()} for r in rows]).resolve()


def documents_for(tx, body, rows):
    answer = run_rows(tx, body, rows)
    return list(answer.as_concept_documents()) if answer is not None else []


def rows_for(tx, body, rows):
    answer = run_rows(tx, body, rows)
    return list(answer.as_concept_rows()) if answer is not None else []


def documents(tx, body, params=None):
    return list(run(tx, body, params).as_concept_documents())


def concept_rows(tx, body, params=None):
    return list(run(tx, body, params).as_concept_rows())


def parse_datetime(text):
    """Parse a datetime-tz as fetch returns it ('2025-01-10T09:05:00.000000000+00:00'), to microseconds."""
    if text is None:
        return None
    match = re.match(r"^(.*T\d\d:\d\d:\d\d)(?:\.(\d+))?(Z|[+-]\d\d:\d\d)$", text)
    if not match:
        raise ValueError(f"unexpected datetime format: {text!r}")
    base, fraction, zone = match.groups()
    micro = (fraction or "0")[:6].ljust(6, "0")
    return datetime.fromisoformat(f"{base}.{micro}{'+00:00' if zone == 'Z' else zone}")
