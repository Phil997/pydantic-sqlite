import os
from uuid import uuid4

import pytest
from pydantic import BaseModel
from pydantic_sqlite import DataBase, DB_Handler
from testfixtures import TempDirectory

LENGTH = 10
TEST_DB_NAME = "test.db"
TEST_TABLE_NAME = "test.db"

class Foo(BaseModel):
    uuid: str
    name: str


@pytest.fixture()
def dir():
    with TempDirectory() as dir:
        yield dir


@pytest.fixture()
def db():
    db = DataBase()
    for _ in range(LENGTH):
        foo = Foo(uuid=str(uuid4()), name="unitest")
        db.add(TEST_TABLE_NAME, foo)
    assert len(list(db(TEST_TABLE_NAME))) == LENGTH
    return db


def test_save_with_file_ending(dir, db):
    db.save(f"{dir.path}\\hello.db")
    assert "hello.db" in os.listdir(dir.path)
    assert len(os.listdir(dir.path)) == 1, "detect more than one file in path"

def test_save_with_automatic_add_file_ending(dir, db):
    db.save(f"{dir.path}\\world")
    assert "world.db" in os.listdir(dir.path)
    assert len(os.listdir(dir.path)) == 1, "detect more than one file in path"

def test_save_override_exicsting_db(dir, db):
    db.save(f"{dir.path}\\{TEST_DB_NAME}")
    assert TEST_DB_NAME in os.listdir(dir.path)
    
    for _ in range(LENGTH):
        foo = Foo(uuid=str(uuid4()), name="unitest")
        db.add('Foo2', foo)
    assert len(db._db.table_names()) == 3

    db.save(f"{dir.path}\\{TEST_DB_NAME}")
    assert TEST_DB_NAME in os.listdir(dir.path)
    assert len(os.listdir(dir.path)) == 1, "detect more than one file in path"

def test_load_raise_Exception_not_existing(dir, db):
    with pytest.raises(FileNotFoundError):
        db.load(f"{dir.path}\\{TEST_DB_NAME}")

def test_save_and_load(dir, db):
    db.save(f"{dir.path}\\{TEST_DB_NAME}")
    assert TEST_DB_NAME in os.listdir(dir.path)
    assert len(os.listdir(dir.path)) == 1, "detect more than one file in path"

    db = DataBase()
    db.load(f"{dir.path}\\{TEST_DB_NAME}")
    assert len(db._db.table_names()) == 2
    assert len(list(db(TEST_TABLE_NAME))) == LENGTH
    
    for foo in db(TEST_TABLE_NAME):
        assert issubclass(foo.__class__, BaseModel)
        assert isinstance(foo, Foo)

def test_handler_return_DataBase(dir):
    with DB_Handler() as db:
        assert isinstance(db, DataBase)

def test_handler_save_DataBase(dir):
    with DB_Handler() as db:
        for _ in range(LENGTH):
            foo = Foo(uuid=str(uuid4()), name="unitest")
            db.add(TEST_TABLE_NAME, foo)
        db.save(f"{dir.path}\\{TEST_DB_NAME}")
    
    assert TEST_DB_NAME in os.listdir(dir.path)

def test_handler_load(dir, db):
    db.save(f"{dir.path}\\{TEST_DB_NAME}")
    with DB_Handler(f"{dir.path}\\{TEST_DB_NAME}") as testdb:

        for foo in testdb(TEST_TABLE_NAME):
            assert issubclass(foo.__class__, BaseModel)
            assert isinstance(foo, Foo)

def test_handler_save_ExceptionDB_on_exception(dir, db):
    db.save(f"{dir.path}\\{TEST_DB_NAME}")
    with pytest.raises(ZeroDivisionError):
        with DB_Handler(f"{dir.path}\\{TEST_DB_NAME}") as _:
            1/0
    assert f"{TEST_DB_NAME[:-3]}_crash.db" in os.listdir(dir.path)

def test_handler_save_multiple_ExceptionDB_on_exception(dir, db):
    db.save(f"{dir.path}\\{TEST_DB_NAME}")

    with pytest.raises(ZeroDivisionError):
        with DB_Handler(f"{dir.path}\\{TEST_DB_NAME}") as _:
            1/0
    assert f"{TEST_DB_NAME[:-3]}_crash.db" in os.listdir(dir.path)

    with pytest.raises(ZeroDivisionError):
        with DB_Handler(f"{dir.path}\\{TEST_DB_NAME}") as _:
            1/0
    assert f"{TEST_DB_NAME[:-3]}_crash_(1).db" in os.listdir(dir.path)
    
