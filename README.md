# pydantic-sqlite  <!-- omit in toc -->

![Python](https://img.shields.io/badge/python-3.8%20|%203.9%20|%203.10%20|%203.11%20|%203.12%20|%203.13-blue?logo=python&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-brightgreen.svg)
[![codecov](https://codecov.io/github/Phil997/pydantic-sqlite/graph/badge.svg?token=MCCXX7XF9V)](https://codecov.io/github/Phil997/pydantic-sqlite)


A lightweight package for storing `pydantic` `BaseModel` in a `SQLite` database.

You can store any `BaseModel` instance directly in the database, and when querying a table, you receive fully reconstructed `BaseModel` objects — ready to use, just like your originals.

- [Installation](#installation)
- [Usage](#usage)
  - [Basic Example](#basic-example)
  - [Nested Example](#nested-example)
  - [Nested Example without Foreign Table](#nested-example-without-foreign-table)
  - [Nested with different primary keys](#nested-with-different-primary-keys)
  - [FailSafeDataBase](#failsafedatabase)

## Installation

```
pip install pydantic-sqlite
```

## Usage

### Basic Example
Create two instances of the class `Person` and store them in the 'Test' table of the database. Then, retrieve and display all records from the 'Test' table through iteration. Per default DataBase uses `uuid` as the primary-key in tha table.

```python
from pydantic_sqlite import DataBase
from pydantic import BaseModel

class Person(BaseModel):
    uuid: str
    name: str
    age: int

# Create two Person instances
person1 = Person(uuid="abc", name="Yoda", age=900)
person2 = Person(uuid="def", name="Leia", age=23)

db = DataBase()
db.add("Test", person1)
db.add("Test", person2)

for x in db("Test"):
    assert isinstance(x, Person)
    print(x)

#>>> uuid='abc' name='Yoda' age=900
#>>> uuid='def' name='Leia' age=23
```

### Nested Example

Instantiate an address object and two person objects, with each person having an attribute of the address type. Upon adding the person to the database, the database requires the foreign table 'Adresses' to establish the foreign key relationship. Consequently, when iterating over the 'Persons' table, it enables the reconstruction of complete 'Person' objects, each possessing an attribute of the 'Address' type.

```python
from pydantic_sqlite import DataBase
from pydantic import BaseModel

class Address(BaseModel):
    uuid: str
    town: str
    street: str
    number: int

class Person(BaseModel):
    uuid: str
    name: str
    address: Address

address = Address(uuid="abc", town="Mos Espa", street="Dustwind Street", number=67)
person1 = Person(uuid="def", name="Anakin", address=address)

db = DataBase()
db.add("Adresses", address)
db.add("Persons", person1, foreign_tables={'address': 'Adresses'})

for x in db("Adresses"):
    assert isinstance(x, Address)
    print(x)

for y in db("Persons"):
    assert isinstance(y, Person)
    print(y)

#>>> uuid='abc' town='Mos Espa' street='Dustwind Street' number=67
#>>> uuid='def' name='Anakin' address=Address(uuid='abc', town='Berlin', street='Dustwind Street', number=67)
```

### Nested Example without Foreign Table
If you prefer to avoid an extra table, you have the option to store an object of the BaseModel type differently.

In this scenario, the address object isn't stored in a separate table but rather as a string within a column of the 'Persons' table. To achieve this, the Address class includes the SQConfig class, which must define the convert method, specifying how the object should be stored in SQLite. Upon retrieval, an Address object is reconstructed from the stored string using a field_validator.

```python
from uuid import uuid4
from pydantic import BaseModel, field_validator
from pydantic_sqlite import DataBase

class Address(BaseModel):
    town: str
    street: str

    class SQConfig:
        special_insert: bool = True

        def convert(obj):
            return f"{obj.town},{obj.street}"

class Person(BaseModel):
    uuid: str
    name: str
    address: Address

    @field_validator('address', mode="before")
    def validate(cls, v):
        if isinstance(v, Address):
            return v
        town, street = v.split(',')
        return Address(town=town, street=street)

address = Address(town="Berlin", street="Bahnhofstraße 67")
person1 = Person(uuid=str(uuid4()), name="Bob", address=address)
person2 = Person(uuid=str(uuid4()), name="Alice", address=address)

db = DataBase()
db.add("Persons", person1)
db.add("Persons", person2)

for y in db("Persons"):
    assert isinstance(y, Person)
    print(y)

#>>> uuid='...' name='Bob' address=Address(town='Berlin', street='Bahnhofstraße 67')
#>>> uuid='...' name='Alice' address=Address(town='Berlin', street='Bahnhofstraße 67')

for y in db("Persons", where='name= :name', where_args={'name': 'Alice'}):
    assert isinstance(y, Person)
    print(y)
#>>> uuid='...' name='Alice' address=Address(town='Berlin', street='Bahnhofstraße 67')
```

### Nested with different primary keys

This example demonstrates how to handle nested models where each table uses a different primary key, and how to manage foreign key relationships between them. Here, a `CarRegistration` contains a `Person` and a `Car`, and the `Car` itself contains a list of `Wheel` objects. Each model has its own unique primary key, and the relationships are established using the `foreign_tables` argument.

```python
from typing import List
from pydantic import BaseModel
from pydantic_sqlite import DataBase

class Person(BaseModel):
    uuid: str
    name: str

class Wheel(BaseModel):
    batch_id: str
    size: int

class Car(BaseModel):
    series_number: str
    model: str
    wheels: List[Wheel]

class CarRegistration(BaseModel):
    id: str
    person: Person
    car: Car

wheels = [Wheel(batch_id=f"P_{i}", size=16) for i in range(4)]
car = Car(series_number="1234", model="Volkswagen Golf", wheels=wheels)
person = Person(uuid="abcd", name="John Doe")
registration = CarRegistration(car=car, person=person, id="fffff")

db = DataBase()

for wheel in wheels:
    db.add("Wheels", wheel, pk='batch_id')
db.add("Cars", car, pk='series_number', foreign_tables={"wheels": "Wheels"})
db.add("Persons", person, pk='uuid')
db.add("CarRegistrations", registration, pk='id', foreign_tables={"car": "Cars", "person": "Persons"})

print(next(db("Persons")))
print(next(db("Cars")))
print(next(db("CarRegistrations")))

#>>> uuid='abcd' name='John Doe'
#>>> series_number='1234' model='Volkswagen Golf' wheels=[Wheel(batch_id='P_0', size=16), Wheel(batch_id='P_1', size=16), Wheel(batch_id='P_2', size=16), Wheel(batch_id='P_3', size=16)]
#>>> id='fffff' person=Person(uuid='abcd', name='John Doe') car=Car(series_number='1234', model='Volkswagen Golf', wheels=[Wheel(batch_id='P_0', size=16), Wheel(batch_id='P_1', size=16), Wheel(batch_id='P_2', size=16), Wheel(batch_id='P_3', size=16)])

```

### FailSafeDataBase
The `FailSafeDataBase` serves as a context manager wrapper for the `DataBase`. The database returned by the context manager functions identically to those in previous examples.

However, the handler offers an added benefit: in case of an exception, it automatically saves a database snapshot with the latest values as `<<dbname>_snapshot.db` (by default). If such a file already exists, the filename is iteratively incremented (e.g., `<<dbname>_snapshot(1).db`).

You can also configure the snapshot suffix using the `snapshot_suffix` argument in the constructor.

For instance, running this example generates two files: `humans.db` and `humans_snapshot.db`. Executing the script again, a snapshot file called `humans_snapshot(1).db` will be created.

```python
from uuid import uuid4
from pydantic import BaseModel
from pydantic_sqlite import FailSafeDataBase

class Person(BaseModel):
    uuid: str
    name: str
    age: int

with FailSafeDataBase("humans", snapshot_suffix="_snapshot.db") as db:
    test1 = Person(uuid=str(uuid4()), name="Bob", age=12)
    db.add("Test", test1)
    for x in db("Test"):
        assert issubclass(x.__class__, BaseModel)
        assert isinstance(x, Person)
        print(x)
    db.save("hello_world.db")

    raise Exception("test")  # simulate an Exception which results in a new snapshot file
```