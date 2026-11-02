"""Phase 0 probe: what vector-related syntax does the installed TypeDB server accept?

Runs each candidate in a disposable database and prints accepted / rejected with the server message.
Usage: uv run python -I scripts/probe_vectors.py
"""

import sys
import uuid

sys.path.insert(0, "src")
from typedb.driver import TransactionType  # noqa: E402

from gupi.typedb.connection import connect, rows, transaction  # noqa: E402

SCHEMA_PROBES = {
    "vector value type (PR #8014 syntax)": 'define attribute emb, value vector(3, "float32");',
    "vector + hnsw index": 'define attribute emb2, value vector(3, "float32") @index(hnsw:cosine);',
    "list-valued attribute": "define attribute embl, value double[];",
    "double attribute, many per owner": "define attribute component, value double; entity chunk, owns component @card(0..);",
    "struct type": "define struct point: x value double, y value double;",
    "string attribute (base64 blob)": "define attribute emb-blob, value string; entity blobbed, owns emb-blob;",
}

READ_PROBES = {
    "cosine_similarity_search function": 'match let $e, $s in cosine_similarity_search(emb, vector([1.0, 0.0, 0.0], "float32"), 0.5);',
    "built-in math functions (abs/round)": "match let $x = abs(-2.5); let $y = round(2.4);",
    "arithmetic incl. power": "match let $x = 2.0 * 3.0 + 1.0 / 2.0; let $p = 2.0 ^ 0.5;",
    "aggregate sum via reduce": "match let $x = 1.5; reduce $s = sum($x);",
}


def first_line(error):
    lines = [line.strip() for line in str(error).splitlines() if line.strip()]
    return " | ".join(lines[:3])[:300]


def main():
    driver = connect()
    print("server version:", driver.server_version() if hasattr(driver, "server_version") else "n/a")
    db = f"gupi-probe-{uuid.uuid4().hex[:8]}"
    driver.databases.create(db)
    try:
        for name, query in SCHEMA_PROBES.items():
            try:
                with transaction(driver, db, TransactionType.SCHEMA) as tx:
                    tx.query(query).resolve()
                print(f"ACCEPTED  {name}")
            except Exception as e:  # report every outcome; this is a probe
                print(f"REJECTED  {name}: {first_line(e)}")
        for name, query in READ_PROBES.items():
            try:
                with transaction(driver, db, TransactionType.READ) as tx:
                    print(f"ACCEPTED  {name}: {len(rows(tx, query))} row(s)")
            except Exception as e:
                print(f"REJECTED  {name}: {first_line(e)}")
    finally:
        driver.databases.get(db).delete()
        driver.close()


if __name__ == "__main__":
    main()
