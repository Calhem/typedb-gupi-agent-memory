"""Connecting to TypeDB 3.14 (verified against typedb-driver 3.14.0 and server 3.14.1).

Settings come from environment variables so no credentials live in code:
GUPI_TYPEDB_ADDRESS (default 127.0.0.1:1734), GUPI_TYPEDB_USERNAME, GUPI_TYPEDB_PASSWORD
(defaults are TypeDB Community Edition's documented local admin account; set real values for any
server that is not a local development instance).
"""

import os
from contextlib import contextmanager

from typedb.driver import Credentials, DriverOptions, DriverTlsConfig, TransactionType, TypeDB


def connect():
    address = os.environ.get("GUPI_TYPEDB_ADDRESS", "127.0.0.1:1734")
    credentials = Credentials(
        os.environ.get("GUPI_TYPEDB_USERNAME", "admin"),
        os.environ.get("GUPI_TYPEDB_PASSWORD", "password"),
    )
    return TypeDB.driver(address, credentials, DriverOptions(DriverTlsConfig.disabled()))


@contextmanager
def transaction(driver, database, kind):
    """Open a transaction; commit write/schema transactions on success, always close."""
    tx = driver.transaction(database, kind)
    try:
        yield tx
        if kind != TransactionType.READ:
            tx.commit()
    finally:
        if tx.is_open():
            tx.close()


def rows(tx, query):
    """Run a match/fetch query and return its answers as a list (concept rows or documents)."""
    answer = tx.query(query).resolve()
    if answer.is_concept_rows():
        return list(answer.as_concept_rows())
    if answer.is_concept_documents():
        return list(answer.as_concept_documents())
    return []
