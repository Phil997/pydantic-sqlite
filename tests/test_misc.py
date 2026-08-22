from enum import Enum
from pathlib import Path
from typing import Union

from pydantic_sqlite._misc import (convert_value_into_union_types,
                                   get_unique_filename, normalize_for_sqlite)
from pydantic_sqlite._utils import row_foreign_ids


class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


def test_normalize_for_sqlite_all_branches():
    value = object()

    assert normalize_for_sqlite(Status.ACTIVE) == "active"
    assert normalize_for_sqlite([Status.ACTIVE, value]) == ["active", value]
    assert normalize_for_sqlite((Status.INACTIVE, value)) == ["inactive", value]
    assert set(normalize_for_sqlite({Status.ACTIVE, Status.INACTIVE})) == {"active", "inactive"}
    assert normalize_for_sqlite({Status.ACTIVE: [Status.INACTIVE]}) == {"active": ["inactive"]}
    assert normalize_for_sqlite(value) is value


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


def test_row_foreign_ids_none():
    assert row_foreign_ids({"person": None}, "person") == []


def test_row_foreign_ids_scalar():
    assert row_foreign_ids({"person": "p1"}, "person") == ["p1"]


def test_row_foreign_ids_json_list():
    assert row_foreign_ids({"employees": '["e1", "e2"]'}, "employees") == ["e1", "e2"]
