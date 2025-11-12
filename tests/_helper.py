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


class Team(BaseModel):
    uuid: str
    employee: Employee


class Address(BaseModel):
    uuid: str
    street: str
    city: str
    zip_code: str


class Car(BaseModel):
    series_number: str
    model: str


class Garage(BaseModel):
    uuid: str
    cars: list[Car]


class CarRegistration(BaseModel):
    id: str
    person: Person
    car: Car
