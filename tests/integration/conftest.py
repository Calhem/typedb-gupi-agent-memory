import uuid

import pytest
from helpers import Clock

from gupi.memory import Memory
from gupi.typedb.connection import connect


@pytest.fixture(scope="session")
def driver():
    try:
        d = connect()
        d.databases.all()
    except Exception as e:
        pytest.skip(f"TypeDB not reachable (run `docker compose up -d`): {e}")
    yield d
    d.close()


@pytest.fixture
def database(driver):
    """A disposable gupi-test-* database, deleted afterwards."""
    name = f"gupi-test-{uuid.uuid4().hex[:8]}"
    driver.databases.create(name)
    yield name
    if driver.databases.contains(name):
        driver.databases.get(name).delete()


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def memory(driver, database, clock):
    return Memory.open(database, packs=("core", "people"), driver=driver, clock=clock)

