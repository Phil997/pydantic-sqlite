# pydantic_sqlite  <!-- omit in toc -->

![Python](https://img.shields.io/badge/python-3.8%20|%203.9%20|%203.10%20|%203.11%20|%203.12%20|%203.13-blue?logo=python&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-brightgreen.svg)


A lightweight package for storing `pydantic` `BaseModel` in a `SQLite` database.

You can store any `BaseModel` instance directly in the database, and when querying a table, you receive fully reconstructed `BaseModel` objects — ready to use, just like your originals.

- [Installation](#installation)
- [Usage](#usage)
  - [Basic Example](#basic-example)
  - [Nested Example](#nested-example)
  - [Nested Example without Foreign Table](#nested-example-without-foreign-table)
  - [DB\_Handler](#db_handler)

## Installation

```
pip install pydantic-sqlite
```

## Usage

### Basic Example
Create two instances of the class `Person` and store them in the 'Test' table of the database. Then, retrieve and display all records from the 'Test' table through iteration:

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

### DB_Handler
The `DB_Handler` serves as a context manager wrapper for the `DataBase`. The database returned by the context manager functions identically to those in previous examples.

However, the handler offers an added benefit: in case of an exception, it automatically saves a database snapshot with the latest values as `<<dbname>_snapshot.db` (by default). If such a file already exists, the filename is iteratively incremented (e.g., `<<dbname>_snapshot(1).db`).

You can also configure the snapshot suffix using the `snapshot_suffix` argument in the constructor.

For instance, running this example generates two files: `humans.db` and `humans_snapshot.db`. Executing the script again, a snapshot file called `humans_snapshot(1).db` will be created.

```python
from uuid import uuid4
from pydantic import BaseModel
from pydantic_sqlite import DB_Handler

class Person(BaseModel):
    uuid: str
    name: str
    age: int

with DB_Handler("humans", snapshot_suffix="_snapshot.db") as db:
    test1 = Person(uuid=str(uuid4()), name="Bob", age=12)
    db.add("Test", test1)
    for x in db("Test"):
        assert issubclass(x.__class__, BaseModel)
        assert isinstance(x, Person)
        print(x)
    db.save("hello_world.db")

    raise Exception("test")  # simulate an Exception which results in a new snapshot file
```