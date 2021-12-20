# pydantic_sqlite
Simple package for storing pydantic BaseModels in an in-memory SQLite database.

## Basic Example
Create two objects of the type TestCase and add them to the database in the table 'Test'. Later, all values in the table are printed while iteration over the Table 'Test'.

``` python
from pydantic_sqlite import DataBase
from pydantic import BaseModel
from uuid import uuid4

class TestCase(BaseModel):
    uuid: str
    name: str 
    age: int
        
test1 = TestCase(uuid=str(uuid4()), name="Bob", age=12)
test2 = TestCase(uuid=str(uuid4()), name="Alice", age=28)

db = DataBase()
db.add("Test", test1)
db.add("Test", test2)

for x in db("Test"):
    assert issubclass(x.__class__, BaseModel)
    assert isinstance(x, TestCase)
    print(x)

#>>> uuid='10d002bc-9941-4943-a46b-82b8214bf618' name='Bob' age=12
#>>> uuid='595fd605-4684-4f78-96a5-8420bdb3fc0f' name='Alice' age=28

```

## Nested Example
Create one object of the type address and two objects of the type person. Each person has an attribute of the type address. 
When adding the person to the database, the database needs the foreign_table 'Adresses' to create the foreign key. This means that when iterating over the table 'Persons', a complete object "Person" can be created again, which has an attribute of the type 'Address'.


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
If you do not want to have an additional table, you can save an object of the BaseModel type differently.

In this example, the address object is not saved as an additional table. It is stored as a string in a column of the table 'Persons'. To realise this, the class `SQConfig` is added to the Address class. This class must contain the method `convert`, which determines how the object is to be stored in SQLite. During the subsequent loading, an object of the type Address is created again from the string with the function pydantic.validator.

```python
from pydantic_sqlite import DataBase
from pydantic import BaseModel, validator
from uuid import uuid4

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
        
    @validator('address', pre=True)
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
The DB_handler provides a wrapper for the DataBase. The database returned by the context manager can be used in the same way as in the previous examples. 

However, the handler has the advantage that if an exception occurs, e.g. a 'ZeroDevisionError', a database with the last values is saved as '<<dbname_crash>>.db'. If this file already exists, the file name is incremented.

This example creates two files hello.db and hello_crash.db If you run this script twice, three files are created: hello.db, hello_crash.db and hello_crash_(1).db
```python
from pydantic_sqlite import DataBase, DB_Handler
from pydantic import BaseModel, validator
from uuid import uuid4

class TestCase(BaseModel):
    uuid: str
    name: str 
    age: int

with DB_Handler("hello") as db:
    test1 = TestCase(uuid=str(uuid4()), name="Bob", age=12)
    db.add("Test", test1)
    for x in db("Test"):
        assert issubclass(x.__class__, BaseModel)
        assert isinstance(x, TestCase)
        print(x)
    db.save("hello_world.db")
    
    1/0

#>>> uuid='04d6dfad-0ce5-4222-8686-22348e1f0c0b' name='Bob' age=12
#>>> ---------------------------------------------------------------------------
#>>> ZeroDivisionError    Traceback (most recent call last)
#>>> ~\AppData\Local\Temp/ipykernel_20124/1430346317.py in <module>
#>>>      17     db.save("hello_world.db")
#>>>      18 
#>>> ---> 19     1/0
#>>> 
#>>> ZeroDivisionError: division by zero
```