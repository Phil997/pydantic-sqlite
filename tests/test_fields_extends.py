import string
from enum import Enum, IntEnum
from random import choice
from typing import Any, Literal, Optional, Union
from uuid import uuid4

try:
    from enum import StrEnum
except ImportError:
    class StrEnum(str, Enum):
        pass

from hypothesis import given
from hypothesis import strategies as st
from pydantic import BaseModel

from pydantic_sqlite import DataBase

from ._helper import SQLITE_INTEGERS_MAX, SQLITE_INTEGERS_MIN

VALID_LITERALS = ['hello', 'hi', 'hey']


class Example(BaseModel):
    uuid: str
    ex_Literal: Literal['hello', 'hi', 'hey']
    ex_list_any: list[Any]
    ex_any: Any
    ex_optional: Optional[str]
    ex_union: Union[int, str]


class StringEnum(str, Enum):
    FOO = "FOO"
    BAR = "BAR"


class NativeStringEnum(StrEnum):
    FOO = "FOO"
    BAR = "BAR"


class IntegerEnum(Enum):
    LOW = 1
    HIGH = 2


class IntegerIntEnum(IntEnum):
    LOW = 1
    HIGH = 2


class EnumValues(BaseModel):
    id: str
    string_value: StringEnum
    str_enum_value: NativeStringEnum
    integer_value: IntegerEnum
    int_enum_value: IntegerIntEnum
    any_value: Any
    union_value: Union[IntegerEnum, str]
    list_value: list[IntegerEnum]
    dict_value: dict[str, StringEnum]


@st.composite
def example_values(draw):
    return dict(
        uuid=str(uuid4()),
        ex_Literal=draw(st.sampled_from(VALID_LITERALS)),
        ex_list_any=draw(st.lists(st.text())),
        ex_any=draw(st.text()),
        ex_optional=draw(st.one_of(st.text(), st.none())),
        ex_union=draw(st.one_of(
            st.text(alphabet=string.ascii_letters),
            st.integers(min_value=SQLITE_INTEGERS_MIN, max_value=SQLITE_INTEGERS_MAX)
        )),
    )


def test_enum_types_roundtrip():
    db = DataBase()
    values = EnumValues(
        id="1",
        string_value=StringEnum.FOO,
        str_enum_value=NativeStringEnum.BAR,
        integer_value=IntegerEnum.HIGH,
        int_enum_value=IntegerIntEnum.LOW,
        any_value=StringEnum.BAR,
        union_value=IntegerEnum.LOW,
        list_value=[IntegerEnum.LOW, IntegerEnum.HIGH],
        dict_value={"buy": StringEnum.FOO},
    )

    db.add("EnumValues", values, pk="id")

    raw = next(db._db["EnumValues"].rows)
    assert raw["string_value"] == "FOO"
    assert raw["str_enum_value"] == "BAR"
    assert raw["integer_value"] == 2
    assert raw["int_enum_value"] == 1
    assert raw["any_value"] == "BAR"
    assert raw["union_value"] == 1
    assert raw["list_value"] == "[1, 2]"
    assert raw["dict_value"] == '{"buy": "FOO"}'

    result = db.model_from_table("EnumValues", "1")
    assert result == values
    assert isinstance(result.string_value, StringEnum)
    assert isinstance(result.str_enum_value, NativeStringEnum)
    assert isinstance(result.integer_value, IntegerEnum)
    assert isinstance(result.int_enum_value, IntegerIntEnum)
    assert result.any_value == "BAR"
    assert isinstance(result.union_value, IntegerEnum)
    assert all(isinstance(item, IntegerEnum) for item in result.list_value)
    assert all(isinstance(item, StringEnum) for item in result.dict_value.values())


@given(example_values())
def test_various_types_extend(values: dict):
    db = DataBase()
    ex = Example(**values)
    db.add("Test", ex)
    for x in db('Test'):
        assert isinstance(x, Example)

    x = db.model_from_table('Test', ex.uuid)
    assert isinstance(x, Example)
    assert x == ex
    assert x.ex_optional is None or isinstance(x.ex_optional, str)


@given(st.lists(example_values(), min_size=1))
def test_save_and_get_while_iteration_multiple(values: dict):
    db = DataBase()
    examples = [Example(**vls) for vls in values]
    for ex in examples:
        db.add("Test", ex)
    db_values = list(db("Test"))
    assert len(examples) == len(db_values)
    for value in db_values:
        assert isinstance(value, Example)
        assert value in examples
        assert value.ex_optional is None or isinstance(value.ex_optional, str)


@given(st.lists(example_values(), min_size=1))
def test_save_and_get_from_table_multiple(values: dict):
    db = DataBase()
    examples = [Example(**vls) for vls in values]
    for ex in examples:
        db.add("Test", ex)
    for _ in range(10):
        ex = choice(examples)
        res = db.model_from_table('Test', ex.uuid)
        assert isinstance(res, Example)
        assert res == ex
