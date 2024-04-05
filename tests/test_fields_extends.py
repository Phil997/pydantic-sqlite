from random import choice
from typing import Any, List, Literal, Optional, Union
from uuid import uuid4

from hypothesis import given
from hypothesis import strategies as st
from pydantic import BaseModel

from pydantic_sqlite import DataBase

VALID_LITERALS = ['hello', 'hi', 'hey']


class Example(BaseModel):
    uuid: str
    ex_Literal: Literal['hello', 'hi', 'hey']
    ex_list_any: List[Any]
    ex_any: Any
    ex_optional: Optional[str]
    ex_union: Union[str, int]


@st.composite
def example_values(draw):
    return dict(
        uuid=uuid4().__str__(),
        ex_Literal=draw(st.sampled_from(VALID_LITERALS)),
        ex_list_any=draw(st.lists(st.text())),
        ex_any=draw(st.text()),
        ex_optional=draw(st.sampled_from(elements=[draw(st.text()), None])),
        ex_union=draw(st.sampled_from(elements=[draw(st.text()), draw(st.integers())])),
    )


@given(example_values())
def test_save_and_get_while_iterration(values):
    db = DataBase()
    test1 = Example(**values)
    db.add("Test", test1)

    for x in db('Test'):
        assert issubclass(x.__class__, BaseModel)
        assert isinstance(x, Example)
        assert x == test1
        assert x.ex_optional is None or isinstance(x.ex_optional, str)


@given(example_values())
def test_save_and_get_from_table(values):
    db = DataBase()
    test1 = Example(**values)
    db.add("Test", test1)

    x = db.value_from_table('Test', test1.uuid)
    assert issubclass(x.__class__, BaseModel)
    assert isinstance(x, Example)
    assert x == test1
    assert x.ex_optional is None or isinstance(x.ex_optional, str)


@given(example_values())
def test_save_and_check_is_in_table(values):
    db = DataBase()
    test1 = Example(**values)
    db.add("Test", test1)

    assert db.uuid_in_table('Test', test1.uuid)
    assert db.value_in_table('Test', test1)


@given(st.lists(example_values(), min_size=1))
def test_save_and_get_while_iterration_multiple(values):
    db = DataBase()

    examples = [Example(**vls) for vls in values]
    for ex in examples:
        db.add("Test", ex)

    db_values = [ex for ex in db("Test")]
    for value in db_values:
        assert issubclass(value.__class__, BaseModel)
        assert isinstance(value, Example)
        assert value in examples
        assert value.ex_optional is None or isinstance(value.ex_optional, str)
    assert len(examples) == len(db_values)


@given(st.lists(example_values(), min_size=1))
def test_save_and_get_from_table_multiple(values):
    db = DataBase()

    examples = [Example(**vls) for vls in values]
    for ex in examples:
        db.add("Test", ex)

    for _ in range(10):
        ex = choice(examples)
        res = db.value_from_table('Test', ex.uuid)
        assert issubclass(res.__class__, BaseModel)
        assert isinstance(res, Example)
        assert res == ex
