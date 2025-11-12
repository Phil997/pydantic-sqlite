import string
from random import choice
from typing import Any, Literal, Optional, Union
from uuid import uuid4

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
