import os
from uuid import uuid4

import pytest
from pydantic import BaseModel

from pydantic_sqlite import DataBase, DB_Handler

from ._helper import LENGTH, TEST_DB_NAME, TEST_TABLE_NAME, Person


class DummyExeption(Exception):
    ...


def test_context_manager():
    with DB_Handler("mytest") as db:
        assert isinstance(db, DataBase)

    handler = DB_Handler("mytest")
    with handler:
        with pytest.raises(RuntimeError):
            with handler:
                ...  # re-entering the context manager should raise an error


def test_save_DataBase(dir: str):
    with DB_Handler("mytest", snapshot_suffix="_snapshot.db") as db:
        for _ in range(LENGTH):
            person = Person(uuid=str(uuid4()), name="unitest")
            db.add(TEST_TABLE_NAME, person)
        db.save(dir + TEST_DB_NAME)

    assert TEST_DB_NAME in os.listdir(dir)


def test_load(dir: str, db: DataBase):
    db.save(dir + TEST_DB_NAME)
    with DB_Handler(dbname=dir + TEST_DB_NAME, snapshot_suffix="_snapshot.db") as testdb:
        for person in testdb(TEST_TABLE_NAME):
            assert issubclass(person.__class__, BaseModel)
            assert isinstance(person, Person)


def test_save_snapshot_on_exception(dir: str, db: DataBase):
    db.save(dir + TEST_DB_NAME)

    with pytest.raises(KeyError):
        with DB_Handler(dir + TEST_DB_NAME, snapshot_suffix="_snapshot.db") as _:
            raise KeyError()
    assert f"{TEST_DB_NAME[:-3]}_snapshot.db" in os.listdir(dir)

    with pytest.raises(DummyExeption):
        with DB_Handler(dir + TEST_DB_NAME, snapshot_suffix="_snapshot.db") as _:
            raise DummyExeption()
    assert f"{TEST_DB_NAME[:-3]}_snapshot(1).db" in os.listdir(dir)
