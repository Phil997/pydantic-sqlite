from typing import List
from uuid import uuid4

from pydantic import BaseModel, validator

from pydantic_sqlite import DataBase


class Foo(BaseModel):
    uuid: str
    name: str


class Bar(BaseModel):
    uuid: str
    foo: Foo


class Baz(BaseModel):
    uuid: str
    bar: Bar


class FooList(BaseModel):
    uuid: str
    testcase: List[Foo]


class Hello(BaseModel):
    name: str

    class SQConfig:
        special_insert: bool = True

        def convert(obj):
            return f"_{obj.name}"


class World(BaseModel):
    uuid: str
    hello: Hello

    @validator('hello', pre=True)
    def validate(cls, v):
        if isinstance(v, Hello):
            return v
        return Hello(name=v[1:])


class Example3(BaseModel):
    uuid: str
    data: List[Hello]

    @validator('data', pre=True)
    def validate(cls, v):
        if not isinstance(v, list):
            raise ValueError("value is not a list")

        def inner():
            for x in v:
                yield x if isinstance(x, Hello) else Hello(name=x[1:])
        return list(inner())


def test_nested_BaseModels_Level_0():
    db = DataBase()
    foo = Foo(uuid=str(uuid4()), name="unitest")

    db.add('Foo', foo)
    assert db.value_in_table('Foo', foo)


def test_nested_BaseModels_Level_1():
    db = DataBase()
    foo = Foo(uuid=str(uuid4()), name="unitest")
    bar = Bar(uuid=str(uuid4()), foo=foo)

    db.add('Foo', foo)
    assert db.value_in_table('Foo', foo)

    db.add('Bar', bar, foreign_tables={"foo": "Foo"})
    assert db.value_in_table('Bar', bar)
    assert isinstance(bar.foo, Foo)


def test_nested_BaseModels_Level_2():
    db = DataBase()
    foo = Foo(uuid=str(uuid4()), name="unitest")
    bar = Bar(uuid=str(uuid4()), foo=foo)
    baz = Baz(uuid=str(uuid4()), bar=bar)

    db.add('Foo', foo)
    assert db.value_in_table('Foo', foo)

    db.add('Bar', bar, foreign_tables={"foo": "Foo"})
    assert db.value_in_table('Bar', bar)
    assert isinstance(bar.foo, Foo)
    assert bar.foo.name == "unitest"

    db.add('Baz', baz, foreign_tables={"bar": "Bar"})
    assert db.value_in_table('Baz', baz)
    assert isinstance(baz.bar, Bar)
    assert isinstance(baz.bar.foo, Foo)
    assert baz.bar.foo.name == "unitest"


def test_nested_BaseModels_in_Typing_List():
    db = DataBase()

    foo1 = Foo(uuid=str(uuid4()), name="unitest")
    foo2 = Foo(uuid=str(uuid4()), name="unitest")
    ex = FooList(uuid=str(uuid4()), testcase=[foo1, foo2])

    db.add('Foo', foo1)
    db.add('Foo', foo2)
    db.add('FooList', ex, foreign_tables={'testcase': 'Foo'})

    assert db.value_in_table('FooList', ex)
    assert [foo1, foo2] == db.value_from_table('FooList', ex.uuid).testcase


def test_skip_nested():
    db = DataBase()
    hello = Hello(name="unitest")
    world = World(uuid=str(uuid4()), hello=hello)

    db.add('Worlds', world)
    assert db.value_in_table('Worlds', world)
    db.value_from_table('Worlds', world.uuid)


def test_skip_nested_in_List():
    db = DataBase()
    foo = Hello(name="foo")
    bar = Hello(name="bar")
    ex = Example3(uuid=str(uuid4()), data=[foo, bar])

    db.add('Example', ex)
    assert db.value_in_table('Example', ex)
    ex_res = db.value_from_table('Example', ex.uuid)
    assert ex_res.data == [foo, bar]


def test_update_the_nested_model():
    db = DataBase()
    foo = Foo(uuid=str(uuid4()), name="unitest")
    bar = Bar(uuid=str(uuid4()), foo=foo)

    db.add('Foo', foo)
    db.add('Bar', bar, foreign_tables={"foo": "Foo"})

    bar.foo.name = "new_value"
    db.add('Bar', bar, foreign_tables={"foo": "Foo"})

    assert db.value_from_table('Bar', bar.uuid).foo.name == "new_value"


def test_update_the_nested_model_indirect():
    db = DataBase()
    foo = Foo(uuid=str(uuid4()), name="unitest")
    bar = Bar(uuid=str(uuid4()), foo=foo)

    db.add('Foo', foo)
    db.add('Bar', bar, foreign_tables={"foo": "Foo"})

    foo.name = "new_value"
    db.add('Foo', foo)

    assert db.value_from_table('Bar', bar.uuid).foo.name == "new_value"
