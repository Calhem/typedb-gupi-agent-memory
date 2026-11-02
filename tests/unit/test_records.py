from datetime import datetime, timezone

import pytest

from gupi.records import Claim, Evidence, Observation, Referent, proposition_key
from gupi.temporal import ValidTime

E = (Evidence("obs:1", 0, 5),)
ROLES = {"report": "p:alice", "manager": "p:bob"}


def test_ids_are_stable_and_content_derived():
    a = Observation("src:hr", "row-1", "Alice reports to Bob.")
    assert a.id == Observation("src:hr", "row-1", "Alice reports to Bob.").id
    assert a.id != Observation("src:hr", "row-1", "Alice reports to Sam.").id  # changed content: new observation
    assert a.id != Observation("src:wiki", "row-1", "Alice reports to Bob.").id  # other source


def test_claims_about_the_same_proposition_share_a_key_but_not_an_id():
    one = Claim("reporting", ROLES, E)
    other = Claim("reporting", {"manager": "p:bob", "report": "p:alice"}, (Evidence("obs:2"),))
    assert one.proposition_key == other.proposition_key == proposition_key("reporting", ROLES)
    assert one.id != other.id
    later = Claim("reporting", ROLES, E, valid=ValidTime(to_earliest=datetime(2025, 1, 1, tzinfo=timezone.utc)))
    assert later.id != one.id and later.proposition_key == one.proposition_key


def test_records_validate_their_inputs():
    with pytest.raises(ValueError):
        Referent("p:x", "person; delete")
    with pytest.raises(ValueError):
        Claim("reporting", {"report } match": "p:x"}, E)
    with pytest.raises(ValueError):
        Claim("reporting", ROLES, ())
    with pytest.raises(ValueError):
        Claim("reporting", ROLES, E, confidence=1.5)
