from typing import List
from uuid import uuid4

from pydantic import BaseModel, field_validator

from pydantic_sqlite import DataBase

from ._helper import Baz, Employee, Person, Team


class Hello(BaseModel):
    name: str

    class SQConfig:
        special_insert: bool = True

        def convert(obj):
            return f"_{obj.name}"


class World(BaseModel):
    uuid: str
    hello: Hello

    @field_validator('hello', mode="before")
    def validate(cls, v):
        if isinstance(v, Hello):
            return v
        return Hello(name=v[1:])


class Example3(BaseModel):
    uuid: str
    data: List[Hello]

    @field_validator('data', mode="before")
    def validate(cls, v):
        if not isinstance(v, list):
            raise ValueError("value is not a list")

        def inner():
            for x in v:
                yield x if isinstance(x, Hello) else Hello(name=x[1:])
        return list(inner())


def test_nested_BaseModels_Level_0():
    db = DataBase()
    person = Person(uuid=str(uuid4()), name="unitest")

    db.add('Person', person)
    assert db.value_in_table('Person', person)


def test_nested_BaseModels_Level_1():
    db = DataBase()
    person = Person(uuid=str(uuid4()), name="unitest")
    employee = Employee(uuid=str(uuid4()), person=person)

    db.add('Person', person)
    assert db.value_in_table('Person', person)

    db.add('Employee', employee, foreign_tables={"person": "Person"})
    assert db.value_in_table('Employee', employee)
    assert isinstance(employee.person, Person)


def test_nested_BaseModels_Level_2():
    db = DataBase()
    person = Person(uuid=str(uuid4()), name="unitest")
    employee = Employee(uuid=str(uuid4()), person=person)
    team = Baz(uuid=str(uuid4()), employee=employee)

    db.add('Person', person)
    assert db.value_in_table('Person', person)

    db.add('Employee', employee, foreign_tables={"person": "Person"})
    assert db.value_in_table('Employee', employee)
    assert isinstance(employee.person, Person)
    assert employee.person.name == "unitest"

    db.add('Baz', team, foreign_tables={"employee": "Employee"})
    assert db.value_in_table('Baz', team)
    assert isinstance(team.employee, Employee)
    assert isinstance(team.employee.person, Person)
    assert team.employee.person.name == "unitest"


def test_nested_BaseModels_in_Typing_List():
    db = DataBase()

    foo1 = Person(uuid=str(uuid4()), name="unitest")
    foo2 = Person(uuid=str(uuid4()), name="unitest")
    ex = Team(uuid=str(uuid4()), testcase=[foo1, foo2])

    db.add('Person', foo1)
    db.add('Person', foo2)
    db.add('Team', ex, foreign_tables={'testcase': 'Person'})

    assert db.value_in_table('Team', ex)
    assert [foo1, foo2] == db.value_from_table('Team', ex.uuid).testcase


def test_skip_nested():
    db = DataBase()
    hello = Hello(name="unitest")
    world = World(uuid=str(uuid4()), hello=hello)

    db.add('Worlds', world)
    assert db.value_in_table('Worlds', world)
    db.value_from_table('Worlds', world.uuid)


def test_skip_nested_in_List():
    db = DataBase()
    person = Hello(name="person")
    employee = Hello(name="employee")
    ex = Example3(uuid=str(uuid4()), data=[person, employee])

    db.add('Example', ex)
    assert db.value_in_table('Example', ex)
    ex_res = db.value_from_table('Example', ex.uuid)
    assert ex_res.data == [person, employee]


def test_update_the_nested_model():
    db = DataBase()
    person = Person(uuid=str(uuid4()), name="unitest")
    employee = Employee(uuid=str(uuid4()), person=person)

    db.add('Person', person)
    db.add('Employee', employee, foreign_tables={"person": "Person"})

    employee.person.name = "new_value"
    db.add('Employee', employee, foreign_tables={"person": "Person"})

    assert db.value_from_table('Employee', employee.uuid).person.name == "new_value"


def test_update_the_nested_model_indirect():
    db = DataBase()
    person = Person(uuid=str(uuid4()), name="unitest")
    employee = Employee(uuid=str(uuid4()), person=person)

    db.add('Person', person)
    db.add('Employee', employee, foreign_tables={"person": "Person"})

    person.name = "new_value"
    db.add('Person', person)

    assert db.value_from_table('Employee', employee.uuid).person.name == "new_value"
