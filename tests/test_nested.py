from typing import List
from uuid import uuid4

from pydantic import BaseModel, field_validator

from pydantic_sqlite import DataBase

from ._helper import Car, CarRegistration, Employee, Garage, Person, Team


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


def test_nested_basemodels_level_0():
    db = DataBase()
    person = Person(uuid=str(uuid4()), name="unitest")

    db.add('Person', person)
    assert db.model_in_table('Person', person)


def test_nested_basemodels_level_2():
    db = DataBase()
    person = Person(uuid=str(uuid4()), name="unitest")
    employee = Employee(uuid=str(uuid4()), person=person)
    team = Team(uuid=str(uuid4()), employee=employee)

    db.add('Person', person)
    assert db.model_in_table('Person', person)

    db.add('Employee', employee, foreign_tables={"person": "Person"})
    assert db.model_in_table('Employee', employee)
    assert isinstance(employee.person, Person)
    assert employee.person.name == "unitest"

    db.add('Team', team, foreign_tables={"employee": "Employee"})
    assert db.model_in_table('Team', team)
    assert isinstance(team.employee, Employee)
    assert isinstance(team.employee.person, Person)
    assert team.employee.person.name == "unitest"


def test_skip_nested():
    db = DataBase()
    hello = Hello(name="unitest")
    world = World(uuid=str(uuid4()), hello=hello)

    db.add('Worlds', world)
    assert db.model_in_table('Worlds', world)
    x = db.model_from_table('Worlds', world.uuid)
    print(x)


def test_skip_nested_in_list():
    db = DataBase()
    person = Hello(name="person")
    employee = Hello(name="employee")
    ex = Example3(uuid=str(uuid4()), data=[person, employee])

    db.add('Example', ex)
    assert db.model_in_table('Example', ex)
    ex_res = db.model_from_table('Example', ex.uuid)
    assert ex_res.data == [person, employee]


def test_update_the_nested_model():
    db = DataBase()
    person = Person(uuid=str(uuid4()), name="unitest")
    employee = Employee(uuid=str(uuid4()), person=person)

    db.add('Person', person)
    db.add('Employee', employee, foreign_tables={"person": "Person"})

    employee.person.name = "new_value"
    db.add('Employee', employee, foreign_tables={"person": "Person"})

    assert db.model_from_table('Employee', employee.uuid).person.name == "new_value"


def test_update_the_nested_model_indirect():
    db = DataBase()
    person = Person(uuid=str(uuid4()), name="unitest")
    employee = Employee(uuid=str(uuid4()), person=person)

    db.add('Person', person)
    db.add('Employee', employee, foreign_tables={"person": "Person"})

    person.name = "new_value"
    db.add('Person', person)

    assert db.model_from_table('Employee', employee.uuid).person.name == "new_value"


def test_alternative_primary_key_mix_list():
    car1 = Car(series_number="1234", model="Volkswagen Golf")
    car2 = Car(series_number="5678", model="Audi A4")

    garage = Garage(uuid="garage1", cars=[car1, car2])

    db = DataBase()
    db.add("Cars", car1, pk='series_number')
    db.add("Cars", car2, pk='series_number')
    db.add("Garages", garage, foreign_tables={"cars": "Cars"})

    assert db.count_entries_in_table("Cars") == 2
    assert db.count_entries_in_table("Garages") == 1

    assert next(db("Garages")) == garage


def test_alternative_primary_key_mix_obj():
    car1 = Car(series_number="1234", model="Volkswagen Golf")
    person = Person(uuid="abcd", name="John Doe")
    owner = CarRegistration(car=car1, person=person, id="fffff")

    db = DataBase()
    db.add("Cars", car1, pk='series_number')
    db.add("Persons", person, pk='uuid')
    db.add("CarRegistrations", owner, pk='id', foreign_tables={"car": "Cars", "person": "Persons"})

    assert next(db("Cars")) == car1
    assert next(db("Persons")) == person
    assert next(db("CarRegistrations")) == owner
