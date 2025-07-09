from datetime import datetime
from random import choice
from typing import List, Optional
from uuid import uuid4

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import BaseModel

from pydantic_sqlite import DataBase

from ._helper import (SQLITE_FLOAT_MAX, SQLITE_FLOAT_MIN, SQLITE_INTEGERS_MAX,
                      SQLITE_INTEGERS_MIN)

settings.register_profile("pydantic-sqlite", deadline=500)
settings.load_profile("pydantic-sqlite")


class Example(BaseModel):
    uuid: str
    ex_str: str
    ex_int: int
    ex_float: float
    ex_bool: bool
    ex_list: List[str]
    ex_date: Optional[datetime] = None


@st.composite
def example_values(draw):
    return dict(
        uuid=str(uuid4()),
        ex_str=draw(st.text()),
        ex_int=draw(st.integers(min_value=SQLITE_INTEGERS_MIN, max_value=SQLITE_INTEGERS_MAX)),
        ex_float=draw(st.floats(min_value=SQLITE_FLOAT_MIN, max_value=SQLITE_FLOAT_MAX)),
        ex_bool=draw(st.booleans()),
        ex_list=draw(st.lists(st.text())),
        ex_date=draw(st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2025, 1, 1))),
    )


def _make_filled_db(values: dict):
    db = DataBase()
    examples = [Example(**vls) for vls in values]
    for ex in examples:
        db.add("Test", ex)
    return db


@settings(deadline=None)
@given(example_values())
def test_save_and_get_while_iteration(values: dict):
    db = DataBase()
    test1 = Example(**values)
    db.add("Test", test1)

    for x in db('Test'):
        assert isinstance(x, Example)
        assert x == test1


@given(example_values())
def test_save_and_get_from_table(values: dict):
    db = DataBase()
    test1 = Example(**values)
    db.add("Test", test1)

    x = db.value_from_table('Test', test1.uuid)
    assert isinstance(x, Example)
    assert x == test1


@given(example_values())
def test_save_and_check_is_in_table(values: dict):
    db = DataBase()
    test1 = Example(**values)
    db.add("Test", test1)

    assert db.value_in_table('Test', test1)
    assert db.value_in_table('Test', test1.uuid)


@given(st.lists(example_values(), min_size=1))
def test_save_and_get_while_iteration_multiple(values: dict):
    db = DataBase()

    examples = [Example(**vls) for vls in values]
    for ex in examples:
        db.add("Test", ex)

    db_values = list(db("Test"))
    for value in db_values:
        assert isinstance(value, Example)
        assert value in examples
    assert len(examples) == len(db_values)


@given(st.lists(example_values(), min_size=1))
def test_save_and_get_from_table_multiple(values: dict):
    db = DataBase()

    examples = [Example(**vls) for vls in values]
    for ex in examples:
        db.add("Test", ex)

    for _ in range(10):
        ex = choice(examples)
        res = db.value_from_table('Test', ex.uuid)
        assert isinstance(res, Example)
        assert res == ex


@given(values=st.lists(example_values(), min_size=10, max_size=20))
@pytest.mark.parametrize(
    "params",
    [
        {'where': 'uuid = :uuid', 'where_args': {'uuid': '123'}},
        {'limit': 2, 'offset': 1},
        {'order_by': 'ex_str'},
        {'order_by': 'ex_str', 'limit': 2},
        {'select': 'ex_str,uuid,ex_int,ex_float,ex_bool,ex_list'},
    ]
)
def test_where_kwargs(values: dict, params: dict):
    filled_db = _make_filled_db(values)

    result = list(filled_db("Test", **params))
    if "where_args" in params:
        for k, v in params["where_args"].items():
            for el in result:
                assert getattr(el, k) == v
    if "limit" in params:
        assert len(result) == params["limit"]
    if "order_by" in params:
        key = params["order_by"]
        if 'DESC' in key.upper():
            assert result == sorted(result, key=lambda x: getattr(x, key), reverse=True)
        else:
            assert result == sorted(result, key=lambda x: getattr(x, key))
    if "select" in params:
        for el in result:
            attrs = [attr.strip() for attr in params["select"].split(",")]
            assert all(hasattr(el, attr) for attr in attrs), el
            if 'ex_date' not in params["select"]:
                assert el.ex_date is None
