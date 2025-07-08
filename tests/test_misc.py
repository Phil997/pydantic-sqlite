from pathlib import Path
from typing import Union

from pydantic_sqlite._misc import (convert_value_into_union_types,
                                   get_unique_filename)


def test_get_unique_filename_existing(tmp_path: Path):
    # Create a file and check that the next unique filename is correct
    file1 = tmp_path / "data.db"
    file1.touch()
    file2 = tmp_path / "data(1).db"
    file2.touch()
    unique = get_unique_filename(str(tmp_path / "data.db"))
    assert unique == str(tmp_path / "data(2).db")


def test_get_unique_filename_no_conflict(tmp_path: Path):
    # If the file does not exist, it should return the same name
    fname = str(tmp_path / "unique.txt")
    assert get_unique_filename(fname) == fname


def test_convert_value_into_union_types_int_str():
    MyUnion = Union[int, float, str]
    assert convert_value_into_union_types(MyUnion, "42") == 42
    assert convert_value_into_union_types(MyUnion, "3.14") == 3.14
    assert convert_value_into_union_types(MyUnion, "hello") == "hello"


def test_convert_value_into_union_types_none():
    MyUnion = Union[int, None]
    assert convert_value_into_union_types(MyUnion, None) is None
    assert convert_value_into_union_types(MyUnion, 5) == 5


def test_convert_value_into_union_types_fallback():
    MyUnion = Union[int, float]
    # If conversion fails, should return the original value
    assert convert_value_into_union_types(MyUnion, "def") == "def"
