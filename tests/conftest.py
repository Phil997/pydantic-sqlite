from uuid import uuid4

import pytest

from pydantic_sqlite import DataBase

from ._helper import LENGTH, TEST_TABLE_NAME, Person


@pytest.fixture()
def sample_db() -> DataBase:
    db = DataBase()
    for _ in range(LENGTH):
        person = Person(uuid=str(uuid4()), name="unitest")
        db.add(TEST_TABLE_NAME, person)
    assert len(list(db(TEST_TABLE_NAME))) == LENGTH
    return db
