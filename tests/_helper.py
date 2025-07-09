from typing import List

from pydantic import BaseModel

LENGTH = 10
TEST_DB_NAME = "test.db"
TEST_TABLE_NAME = "test.db"

SQLITE_INTEGERS_MAX = 2**63-1
SQLITE_INTEGERS_MIN = -2**63
SQLITE_FLOAT_MIN = -1.7976931348623157e+308
SQLITE_FLOAT_MAX = 1.7976931348623157e+308


class Person(BaseModel):
    uuid: str
    name: str


class Employee(BaseModel):
    uuid: str
    person: Person


class Baz(BaseModel):
    uuid: str
    employee: Employee


class Team(BaseModel):
    uuid: str
    testcase: List[Person]


class Car(BaseModel):
    series_number: str
    model: str
