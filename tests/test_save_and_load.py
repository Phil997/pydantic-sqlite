import os
from unittest import mock
from uuid import uuid4

import pytest
from pydantic import BaseModel
from testfixtures import TempDirectory

from pydantic_sqlite import DataBase

from ._helper import LENGTH, TEST_DB_NAME, TEST_TABLE_NAME, Person


@pytest.fixture()
def persistent_db(dir):
    db = DataBase(filename_or_conn=(dir + TEST_DB_NAME))
    for _ in range(LENGTH):
        person = Person(uuid=str(uuid4()), name="unitest")
        db.add(TEST_TABLE_NAME, person)
    assert len(list(db(TEST_TABLE_NAME))) == LENGTH
    return db


def test_save_with_file_ending(dir, db):
    db.save(dir + "hello.db")
    assert "hello.db" in os.listdir(dir)
    assert len(os.listdir(dir)) == 1, "detect more than one file in path"


def test_save_with_automatic_add_file_ending(dir, db):
    db.save(dir + "hello")
    assert "hello.db" in os.listdir(dir)
    assert len(os.listdir(dir)) == 1, "detect more than one file in path"


def test_save_override_existing_db(dir, db):
    db.save(dir + TEST_DB_NAME)
    assert TEST_DB_NAME in os.listdir(dir)

    for _ in range(LENGTH):
        person = Person(uuid=str(uuid4()), name="unitest")
        db.add("Foo2", person)
    assert len(db._db.table_names()) == 3

    db.save(dir + TEST_DB_NAME)
    assert TEST_DB_NAME in os.listdir(dir)
    assert len(os.listdir(dir)) == 1, "detect more than one file in path"


def test_backup_file_on_existing_file(dir, db):
    with TempDirectory() as d1:
        with mock.patch("pydantic_sqlite._core.tempfile.mkdtemp", lambda: d1.path) as _:
            db.save(dir + TEST_DB_NAME)
        assert TEST_DB_NAME in os.listdir(dir)
        assert TEST_DB_NAME in os.listdir(d1.path)
        assert "_backup.db" not in os.listdir(d1.path)

    with TempDirectory() as d2:
        with mock.patch("pydantic_sqlite._core.tempfile.mkdtemp", lambda: d2.path) as _:
            db.save(dir + TEST_DB_NAME)

        assert TEST_DB_NAME in os.listdir(dir)
        assert TEST_DB_NAME in os.listdir(d2.path)
        assert "_backup.db" in os.listdir(d2.path)


def test_load_raise_Exception_not_existing(dir, db):
    with pytest.raises(FileNotFoundError):
        db.load(dir + TEST_DB_NAME)


def test_save_and_load(dir, db):
    db.save(dir + TEST_DB_NAME)
    assert TEST_DB_NAME in os.listdir(dir)
    assert len(os.listdir(dir)) == 1, "detect more than one file in path"

    db = DataBase()
    db.load(dir + TEST_DB_NAME)
    assert len(db._db.table_names()) == 2
    assert len(list(db(TEST_TABLE_NAME))) == LENGTH

    for person in db(TEST_TABLE_NAME):
        assert issubclass(person.__class__, BaseModel)
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
