import os
from pathlib import Path
from unittest import mock
from uuid import uuid4

import pytest
from pydantic import BaseModel
from testfixtures import TempDirectory

from pydantic_sqlite import DataBase

from ._helper import LENGTH, TEST_DB_NAME, TEST_TABLE_NAME, Person


class DummyException(Exception):
    """Dummy exception for testing purposes."""
    ...


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


def test_save_write_backup_file(tmp_path: Path, sample_db: DataBase):
    """
    * tmp_path is the directory where the database should be saved
    * the d1, d2, and d3 are temporary directories created to test the backup functionality
    * The backup is only created if file already exists

    * On the first save, no backup is created, because the file does not exist yet
    * On the second save, a backup is created in the temporary directory
    * On the third save, a backup is created with a custom suffix
    """
    with TempDirectory() as d1:
        with mock.patch("pydantic_sqlite._core.tempfile.mkdtemp", lambda: d1.path):
            sample_db.save(str(tmp_path / TEST_DB_NAME))
        assert TEST_DB_NAME in os.listdir(tmp_path)
        assert f"{TEST_DB_NAME}.backup" not in os.listdir(d1.path)

    with TempDirectory() as d2:
        with mock.patch("pydantic_sqlite._core.tempfile.mkdtemp", lambda: d2.path):
            sample_db.save(str(tmp_path / TEST_DB_NAME))
        assert TEST_DB_NAME in os.listdir(tmp_path)
        assert f"{TEST_DB_NAME}.backup" in os.listdir(d2.path)

    with TempDirectory() as d3:
        with mock.patch("pydantic_sqlite._core.tempfile.mkdtemp", lambda: d3.path):
            sample_db.save(str(tmp_path / TEST_DB_NAME), backup_suffix=".mybackup")
        assert TEST_DB_NAME in os.listdir(tmp_path)
        assert f"{TEST_DB_NAME}.mybackup" in os.listdir(d3.path)


def test_save_write_backup_file_skip(tmp_path: Path, sample_db: DataBase):
    (tmp_path / TEST_DB_NAME).touch()  # Create an empty file to simulate existing database

    with TempDirectory() as d1:
        with mock.patch("pydantic_sqlite._core.tempfile.mkdtemp", lambda: d1.path):
            sample_db.save(str(tmp_path / TEST_DB_NAME))
        assert TEST_DB_NAME in os.listdir(tmp_path)
        assert f"{TEST_DB_NAME}.backup" in os.listdir(d1.path)

    with TempDirectory() as d2:
        with mock.patch("pydantic_sqlite._core.tempfile.mkdtemp", lambda: d2.path):
            sample_db.save(str(tmp_path / TEST_DB_NAME), backup=False)
        assert TEST_DB_NAME in os.listdir(tmp_path)
        assert f"{TEST_DB_NAME}.backup" not in os.listdir(d2.path)


def test_save_log_on_exception(tmp_path: Path, sample_db: DataBase, caplog: pytest.LogCaptureFixture):

    with TempDirectory() as d2:
        with mock.patch("pydantic_sqlite._core.tempfile.mkdtemp", lambda: d2.path):
            expected_backup_file = f"{str(d2.path + os.path.sep + TEST_DB_NAME)}.backup"

            with mock.patch("pydantic_sqlite._core.sqlite3.connect", side_effect=DummyException("Test exception")):
                with pytest.raises(DummyException, match="Test exception"):
                    sample_db.save(str(tmp_path / TEST_DB_NAME))

    assert caplog.records[0].levelname == "WARNING"
    assert caplog.records[0].message == f"saved the backup file under '{expected_backup_file}'"


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
