import os
from pathlib import Path
from unittest import mock
from uuid import uuid4

import pytest
from pydantic import BaseModel
from testfixtures import TempDirectory

from pydantic_sqlite import DataBase

from ._helper import LENGTH, TEST_DB_NAME, TEST_TABLE_NAME, Person


@pytest.fixture()
def persistent_db(tmp_path: Path):
    db = DataBase(filename_or_conn=str(tmp_path / TEST_DB_NAME))
    for _ in range(LENGTH):
        person = Person(uuid=str(uuid4()), name="unitest")
        db.add(TEST_TABLE_NAME, person)
    assert len(list(db(TEST_TABLE_NAME))) == LENGTH
    return db


def test_save_with_file_ending(tmp_path: Path, sample_db: DataBase):
    sample_db.save(str(tmp_path / "hello.db"))
    assert "hello.db" in os.listdir(tmp_path)
    assert len(os.listdir(tmp_path)) == 1


def test_save_with_automatic_add_file_ending(tmp_path: Path, sample_db: DataBase):
    sample_db.save(str(tmp_path / "hello"))
    assert "hello.db" in os.listdir(tmp_path)
    assert len(os.listdir(tmp_path)) == 1


def test_save_override_existing_db(tmp_path: Path, sample_db: DataBase):
    sample_db.save(str(tmp_path / TEST_DB_NAME))
    assert TEST_DB_NAME in os.listdir(tmp_path)

    for _ in range(LENGTH):
        person = Person(uuid=str(uuid4()), name="unitest")
        sample_db.add("Foo2", person)
    assert len(sample_db._db.table_names()) == 3

    sample_db.save(str(tmp_path / TEST_DB_NAME))
    assert TEST_DB_NAME in os.listdir(tmp_path)
    assert len(os.listdir(tmp_path)) == 1


def test_backup_file_on_existing_file(tmp_path: Path, sample_db: DataBase):
    with TempDirectory() as d1:
        with mock.patch("pydantic_sqlite._core.tempfile.mkdtemp", lambda: d1.path):
            sample_db.save(str(tmp_path / TEST_DB_NAME))
        assert TEST_DB_NAME in os.listdir(tmp_path)
        assert TEST_DB_NAME in os.listdir(d1.path)
        assert "_backup.db" not in os.listdir(d1.path)

    with TempDirectory() as d2:
        with mock.patch("pydantic_sqlite._core.tempfile.mkdtemp", lambda: d2.path):
            sample_db.save(str(tmp_path / TEST_DB_NAME))

        assert TEST_DB_NAME in os.listdir(tmp_path)
        assert TEST_DB_NAME in os.listdir(d2.path)
        assert "_backup.db" in os.listdir(d2.path)


def test_load_raise_exception_not_existing(tmp_path: Path, sample_db: DataBase):
    with pytest.raises(FileNotFoundError):
        sample_db.load(str(tmp_path / TEST_DB_NAME))


def test_save_and_load(tmp_path: Path, sample_db: DataBase):
    sample_db.save(str(tmp_path / TEST_DB_NAME))
    assert TEST_DB_NAME in os.listdir(tmp_path)
    assert len(os.listdir(tmp_path)) == 1

    db2 = DataBase()
    db2.load(str(tmp_path / TEST_DB_NAME))
    assert len(db2._db.table_names()) == 2
    assert len(list(db2(TEST_TABLE_NAME))) == LENGTH

    for person in db2(TEST_TABLE_NAME):
        assert isinstance(person, BaseModel)
        assert isinstance(person, Person)


def test_persistent_db_save(persistent_db):
    filename = persistent_db._db.conn.execute("PRAGMA database_list").fetchone()[2]

    with mock.patch("logging.warning") as mock_warning:
        persistent_db.save(TEST_DB_NAME)

        mock_warning.assert_called_once_with(
            f"database is persistent, already stored in a file: {filename}"
        )
        # Verify no file operations were performed
        assert not os.path.exists("_backup.db")

    # Close the database connection before the test ends
    persistent_db._db.conn.close()
