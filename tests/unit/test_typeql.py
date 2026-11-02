from datetime import datetime, timezone

import pytest

from gupi.typeql import given, label, parse_datetime, to_driver


@pytest.mark.parametrize("bad", ["", "Person", "person; delete", "a b", "x$", "-x", "x-", "x--y", 'x"', None, 3])
def test_labels_reject_anything_but_plain_kebab_case(bad):
    with pytest.raises(ValueError):
        label(bad)


def test_labels_accept_schema_style_names():
    assert label("job-title") == "job-title"
    assert label("person2") == "person2"


def test_given_declares_parameter_types():
    when = datetime(2025, 1, 1, tzinfo=timezone.utc)
    header = given({"id": "x", "n": 3, "c": 0.5, "flag": True, "at": when})
    assert header == "given $id: string, $n: integer, $c: double, $flag: boolean, $at: datetime-tz;\n"
    with pytest.raises(ValueError):
        given({"bad name": "x"})
    with pytest.raises(TypeError):
        given({"x": object()})


def test_datetimes_must_be_aware_and_round_trip():
    with pytest.raises(ValueError):
        to_driver(datetime(2025, 1, 1))
    assert str(to_driver(datetime(2025, 1, 1, 12, 0, 0, 250000, tzinfo=timezone.utc))) == \
        "2025-01-01T12:00:00.250000000+00:00"
    assert parse_datetime("2025-01-01T12:00:00.250000000+00:00") == \
        datetime(2025, 1, 1, 12, 0, 0, 250000, tzinfo=timezone.utc)
    assert parse_datetime(None) is None
