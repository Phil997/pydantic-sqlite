# pydantic_sqlite
A lightweight package designed for stroing pydantic BaseModels in an in-memory SQLite database.

## Installation

    pip install pydantic-sqlite

## Basic Example
Creating two instances of the class Person and store them in the 'Test' table of the database. Then, retrieve and display all records from the 'Test' table through iteration."


``` python
from pydantic_sqlite import DataBase
from pydantic import BaseModel
from uuid import uuid4

class Person(BaseModel):
    uuid: str
    name: str 
    age: int
        
test1 = Person(uuid=str(uuid4()), name="Bob", age=12)
test2 = Person(uuid=str(uuid4()), name="Alice", age=28)

db = DataBase()
db.add("Test", test1)
db.add("Test", test2)

for x in db("Test"):
    assert issubclass(x.__class__, BaseModel)
    assert isinstance(x, Person)
    print(x)

#>>> uuid='10d002bc-9941-4943-a46b-82b8214bf618' name='Bob' age=12
#>>> uuid='595fd605-4684-4f78-96a5-8420bdb3fc0f' name='Alice' age=28

```

## Nested Example

Instantiate an address object and two person objects, with each person having an attribute of the address type. Upon adding the person to the database, the database requires the foreign table 'Addresses' to establish the foreign key relationship. Consequently, when iterating over the 'Persons' table, it enables the reconstruction of complete 'Person' objects, each possessing an attribute of the 'Address' type.

```python
from pydantic_sqlite import DataBase
from pydantic import BaseModel
from uuid import uuid4

class Address(BaseModel):
    uuid: str
    town: str
    street: str
    number: int
        
class Person(BaseModel):
    uuid: str
    name: str 
    address: Address

address = Address(uuid=str(uuid4()), town="Berlin", street="Bahnhofstraße", number=67)
person1 = Person(uuid=str(uuid4()), name="Bob", address=address)
person2 = Person(uuid=str(uuid4()), name="Alice", address=address)

db = DataBase()
db.add("Adresses", address)
db.add("Persons", person1, foreign_tables={'address': 'Adresses'})
db.add("Persons", person2, foreign_tables={'address': 'Adresses'})

for x in db("Adresses"):
    assert issubclass(x.__class__, BaseModel)
    assert isinstance(x, Address)
    print(x)

for y in db("Persons"):
    assert issubclass(y.__class__, BaseModel)
    assert isinstance(y, Person)
    print(y)

#>>> uuid='7cd5410e-cfaa-481e-a201-ad04cd959719' town='Berlin' street='Bahnhofstraße' number=67
#>>> uuid='cc1cedaf-dac5-4fc2-a11a-41c6631271a5' name='Bob' address=Address(uuid='7cd5410e-cfaa-481e-a201-ad04cd959719', town='Berlin', street='Bahnhofstraße', number=67)
#>>> uuid='b144ed22-d8a4-46da-8a18-e34c260d7c45' name='Alice' address=Address(uuid='7cd5410e-cfaa-481e-a201-ad04cd959719', town='Berlin', street='Bahnhofstraße', number=67)

```

# Nested Example without foreign Table
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
    assert issubclass(y.__class__, BaseModel)
    assert isinstance(y, Person)
    print(y)

#>>> uuid='802f50d6-b6a2-47f4-bb96-4375790daed9' name='Bob' address=Address(town='Berlin', street='Bahnhofstraße 67')
#>>> uuid='79488c0d-44c8-4a6a-afa3-1ed0b88af4a2' name='Alice' address=Address(town='Berlin', street='Bahnhofstraße 67')
```

# DB_Handler
The DB_handler serves as a wrapper for the DataBase. The database returned by the context manager functions identically to those in previous examples.

However, the handler offers an added benefit: in case of an exception, it automatically saves a database snapshot with the latest values as '<<dbname_crash>>.db'. If such a file already exists, the filename is iteratively incremented.

For instance, running this example generates two files: 'hello.db' and 'hello_crash.db'. Executing the script again, a snapchot file called 'hello_crash(1).db' will be created


```python
from uuid import uuid4
from pydantic import BaseModel
from pydantic_sqlite import DB_Handler

class Person(BaseModel):
    uuid: str
    name: str
    age: int

with DB_Handler("hello") as db:
    test1 = Person(uuid=str(uuid4()), name="Bob", age=12)
    db.add("Test", test1)
    for x in db("Test"):
        assert issubclass(x.__class__, BaseModel)
        assert isinstance(x, Person)
        print(x)
    db.save("hello_world.db")

    raise Exception("test")
```