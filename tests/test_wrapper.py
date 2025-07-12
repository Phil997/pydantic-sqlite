import os
from pathlib import Path
from unittest import mock
from uuid import uuid4

import pytest
from pydantic import BaseModel

from pydantic_sqlite import DataBase, FailSafeDataBase

from ._helper import LENGTH, TEST_DB_NAME, TEST_TABLE_NAME, Person


class DummyExeption(Exception):
    ...


def test_context_manager():
    with FailSafeDataBase("mytest") as db:
        assert isinstance(db, DataBase)

    handler = FailSafeDataBase("mytest")
    with handler:
        with pytest.raises(RuntimeError):
            with handler:
                ...  # re-entering the context manager should raise an error


def test_pass_kwargs(tmp_path: Path):
    with mock.patch("pydantic_sqlite._core._Database") as mocked_sqlite_database:
        with FailSafeDataBase("mytest"):
            mocked_sqlite_database.assert_called_once_with(memory=True)

    with mock.patch("pydantic_sqlite._core._Database") as mocked_sqlite_database:
        with FailSafeDataBase("mytest", snapshot_suffix="_snapshot.db"):
            mocked_sqlite_database.assert_called_once_with(memory=True)

    with mock.patch("pydantic_sqlite._core._Database") as mocked_sqlite_database:
        with FailSafeDataBase("mytest", filename_or_conn=str(tmp_path / TEST_DB_NAME)):
            mocked_sqlite_database.assert_called_once_with(str(tmp_path / TEST_DB_NAME))

    with mock.patch("pydantic_sqlite._core._Database") as mocked_sqlite_database:
        with FailSafeDataBase("mytest", filename_or_conn=str(tmp_path / TEST_DB_NAME), strict=True):
            mocked_sqlite_database.assert_called_once_with(str(tmp_path / TEST_DB_NAME), strict=True)


def test_save_DataBase(tmp_path: Path):
    with FailSafeDataBase(str(tmp_path / "mytest"), snapshot_suffix="_snapshot.db") as db:
        for _ in range(LENGTH):
            person = Person(uuid=str(uuid4()), name="unitest")
            db.add(TEST_TABLE_NAME, person)
        db.save(str(tmp_path / TEST_DB_NAME))

    assert TEST_DB_NAME in os.listdir(tmp_path)


def test_load(tmp_path: Path, sample_db: DataBase):
    sample_db.save(str(tmp_path / TEST_DB_NAME))
    with FailSafeDataBase(dbname=str(tmp_path / TEST_DB_NAME), snapshot_suffix="_snapshot.db") as testdb:
        for person in testdb(TEST_TABLE_NAME):
            assert issubclass(person.__class__, BaseModel)
            assert isinstance(person, Person)


def test_save_snapshot_on_exception(tmp_path: Path, sample_db: DataBase):
    sample_db.save(str(tmp_path / TEST_DB_NAME))
    with pytest.raises(KeyError):
        with FailSafeDataBase(str(tmp_path / TEST_DB_NAME), snapshot_suffix="_snapshot.db") as _:
            raise KeyError()
    assert f"{TEST_DB_NAME[:-3]}_snapshot.db" in os.listdir(tmp_path)
    with pytest.raises(DummyExeption):
        with FailSafeDataBase(str(tmp_path / TEST_DB_NAME), snapshot_suffix="_snapshot.db") as _:
            raise DummyExeption()
    assert f"{TEST_DB_NAME[:-3]}_snapshot(1).db" in os.listdir(tmp_path)
