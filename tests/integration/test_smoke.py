"""Phase 0 smoke test: connection, schema, insert, query and an embedding round trip on the live server."""

import pytest
from typedb.driver import TransactionType

from gupi import embedding
from gupi.typedb.connection import rows, transaction

pytestmark = pytest.mark.integration

SCHEMA = """
define
  attribute name, value string;
  attribute text, value string;
  attribute embedding-f32, value string;
  attribute embedding-model, value string;
  attribute embedding-dim, value integer;
  entity note, owns name @key, owns text, owns embedding-f32, owns embedding-model, owns embedding-dim;
"""

NOTES = {
    "n1": ("Alice became CTO of Acme", [0.9, 0.1, 0.0]),
    "n2": ("Acme hired a new chief technology officer", [0.8, 0.2, 0.1]),
    "n3": ("The bakery sells rye bread", [0.0, 0.1, 0.95]),
}


def test_server_version(driver):
    assert driver.server_version().version.startswith("3.14")


def test_schema_insert_query_and_embedding_round_trip(driver, database):
    with transaction(driver, database, TransactionType.SCHEMA) as tx:
        tx.query(SCHEMA).resolve()
    with transaction(driver, database, TransactionType.WRITE) as tx:
        for key, (text, vector) in NOTES.items():
            tx.query(
                f'insert $n isa note, has name "{key}", has text "{text}", '
                f'has embedding-f32 "{embedding.encode(vector)}", '
                f'has embedding-model "fixture-3d", has embedding-dim {len(vector)};'
            ).resolve()

    with transaction(driver, database, TransactionType.READ) as tx:
        answers = rows(tx, 'match $n isa note, has name $k, has embedding-f32 $e, has embedding-model "fixture-3d";')
        stored = {a.get("k").get_string(): embedding.decode(a.get("e").get_string()) for a in answers}

    assert set(stored) == set(NOTES)
    for key, (_, vector) in NOTES.items():  # float32 round trip is exact to float32 precision
        assert stored[key] == pytest.approx(vector, abs=1e-6)

    query = [1.0, 0.1, 0.0]
    ranked = sorted(stored, key=lambda k: embedding.cosine(query, stored[k]), reverse=True)
    assert ranked == ["n1", "n2", "n3"]


def test_native_vector_syntax_is_still_unsupported(driver, database):
    """Canary: when this fails, the server gained native vectors and docs/adr/0002 should be revisited."""
    with pytest.raises(Exception, match="syntax error"):
        with transaction(driver, database, TransactionType.SCHEMA) as tx:
            tx.query('define attribute emb, value vector(3, "float32");').resolve()


def test_redefining_a_function_needs_redefine(driver, database):
    """Schema migrations must not assume `define` of a function is idempotent."""
    fun = "define fun answer() -> integer: match let $x = 42; return first $x;"
    with transaction(driver, database, TransactionType.SCHEMA) as tx:
        tx.query(fun).resolve()
    with pytest.raises(Exception, match="already exists"):
        with transaction(driver, database, TransactionType.SCHEMA) as tx:
            tx.query(fun).resolve()
    with transaction(driver, database, TransactionType.SCHEMA) as tx:
        tx.query(fun.replace("define", "redefine").replace("42", "43")).resolve()
    with transaction(driver, database, TransactionType.READ) as tx:
        assert rows(tx, "match let $v = answer();")[0].get("v").get_integer() == 43
