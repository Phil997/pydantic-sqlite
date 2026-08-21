# Advanced Usage

## Nested Models with Foreign Keys

Store models that contain other Pydantic models by using foreign key relationships:

```python
from pydantic import BaseModel
from pydantic_sqlite import DataBase

class Address(BaseModel):
    uuid: str
    street: str
    city: str
    country: str

class Person(BaseModel):
    uuid: str
    name: str
    address: Address

db = DataBase()

# First, add the related Address to its table
address = Address(uuid="addr-1", street="123 Main St", city="Berlin", country="Germany")
db.add("Addresses", address)

# Then add Person with foreign_tables parameter
person = Person(uuid="person-1", name="Alice", address=address)
db.add("Persons", person, foreign_tables={"address": "Addresses"})

# Retrieve - the Address is automatically reconstructed
for p in db("Persons"):
    print(f"{p.name} lives in {p.address.city}")
```

## Custom Primary Keys

By default, pydantic-sqlite looks for a `uuid` field as the primary key. You can use any field as the primary key:

```python
from pydantic import BaseModel
from pydantic_sqlite import DataBase

class Car(BaseModel):
    vin: str  # Vehicle Identification Number
    model: str
    year: int

db = DataBase()

car = Car(vin="12345ABCDE", model="Tesla Model 3", year=2024)

# Specify the primary key with pk parameter
db.add("Cars", car, pk="vin")

# Query and retrieve
for car in db("Cars"):
    print(f"{car.year} {car.model}")
```

## Multiple Levels of Nesting

You can nest models at multiple levels, each with its own primary key:

```python
from pydantic import BaseModel
from pydantic_sqlite import DataBase

class Wheel(BaseModel):
    batch_id: str
    diameter: int

class Car(BaseModel):
    series_number: str
    model: str
    wheels: list[Wheel]

class Garage(BaseModel):
    garage_id: str
    owner: str
    car: Car

db = DataBase()

# Create wheels
wheels = [
    Wheel(batch_id="W1", diameter=18),
    Wheel(batch_id="W2", diameter=18),
    Wheel(batch_id="W3", diameter=18),
    Wheel(batch_id="W4", diameter=18),
]

# Add wheels to database
for wheel in wheels:
    db.add("Wheels", wheel, pk="batch_id")

# Create car with wheels
car = Car(series_number="SN123", model="Model S", wheels=wheels)
db.add("Cars", car, pk="series_number", foreign_tables={"wheels": "Wheels"})

# Create garage with car
garage = Garage(garage_id="G1", owner="Alice", car=car)
db.add("Garages", garage, pk="garage_id", foreign_tables={"car": "Cars"})

# Retrieve - full object hierarchy is reconstructed
for g in db("Garages"):
    print(f"{g.owner}'s {g.car.model} has {len(g.car.wheels)} wheels")
```

## Cascading Deletes

By default, `delete` and `delete_where` only remove rows from the specified table. Rows in foreign tables that are referenced by nested models stay untouched:

```python
from pydantic import BaseModel
from pydantic_sqlite import DataBase

class Address(BaseModel):
    uuid: str
    street: str
    city: str

class Person(BaseModel):
    uuid: str
    name: str
    address: Address

db = DataBase()
address = Address(uuid="addr-1", street="123 Main St", city="Berlin")
person = Person(uuid="person-1", name="Alice", address=address)
db.add("Addresses", address)
db.add("Persons", person, foreign_tables={"address": "Addresses"})

# Default: only the Person row is deleted
db.delete("Persons", "person-1")
# -> the Address 'addr-1' remains in the 'Addresses' table
```

Pass `cascade=True` to also delete nested rows in foreign tables. Only rows that are **exclusively** referenced by the deleted row(s) are removed:

```python
db = DataBase()
address = Address(uuid="addr-1", street="123 Main St", city="Berlin")
db.add("Addresses", address)
db.add("Persons", Person(uuid="person-1", name="Alice", address=address), foreign_tables={"address": "Addresses"})

db.delete("Persons", "person-1", cascade=True)
# -> the Address 'addr-1' is deleted as well, because no other row references it
```

Nested rows that are shared between multiple rows are kept:

```python
db = DataBase()
address = Address(uuid="addr-1", street="123 Main St", city="Berlin")
db.add("Addresses", address)
db.add("Persons", Person(uuid="person-1", name="Alice", address=address), foreign_tables={"address": "Addresses"})
db.add("Persons", Person(uuid="person-2", name="Bob", address=address), foreign_tables={"address": "Addresses"})

db.delete("Persons", "person-1", cascade=True)
# -> the Address stays, because 'person-2' still references it
```

`delete_where` supports the same `cascade` parameter:

```python
db.delete_where("Persons", where="name = :name", where_args={"name": "Alice"}, cascade=True)
```

Cascading deletes are recursive and also work with `list` fields, e.g. a `Garage` containing `cars: list[Car]` — deleting the garage with `cascade=True` removes the exclusively referenced cars as well.

## Keyed Nested Collections: `dict[str, BaseModel]`

Models can also contain dictionaries of nested models. The nested models are stored in a foreign table (like `list[BaseModel]`), while the parent row stores a JSON mapping of `{key: primary_key}`. The keys are preserved as-is, so arbitrary labels work:

```python
from decimal import Decimal
from pydantic import BaseModel
from pydantic_sqlite import DataBase

class Position(BaseModel):
    symbol: str
    quantity: int
    avg_cost: Decimal

class Portfolio(BaseModel):
    strategy_id: str
    positions: dict[str, Position] = {}

db = DataBase()

# First, add the related Position to its table
position = Position(symbol="AAPL", quantity=4, avg_cost=Decimal("25.5"))
db.add("Positions", position, pk="symbol")

# Then add Portfolio with foreign_tables parameter
portfolio = Portfolio(strategy_id="m", positions={"AAPL": position})
db.add("Portfolios", portfolio, pk="strategy_id", foreign_tables={"positions": "Positions"})

# Retrieve - the Position objects are fully reconstructed
record = db.model_from_table("Portfolios", "m")
print(record.positions["AAPL"].avg_cost)  # 25.5
```

Dict keys may be arbitrary labels and do not have to match the primary keys of the nested models:

```python
portfolio = Portfolio(strategy_id="m", positions={"main": position})
db.add("Portfolios", portfolio, pk="strategy_id", foreign_tables={"positions": "Positions"})

record = db.model_from_table("Portfolios", "m")
print(record.positions["main"].symbol)  # AAPL
```

`dict[str, Primitive]` fields (e.g. `dict[str, str]`) also round-trip correctly without any `foreign_tables` entry.

## SQConfig: Custom Object Conversion

For models you don't want to store in separate tables, use `SQConfig` with the `special_insert` flag to store them as strings:

```python
from pydantic import BaseModel, field_validator
from pydantic_sqlite import DataBase
from uuid import uuid4

class Address(BaseModel):
    street: str
    city: str

    class SQConfig:
        special_insert: bool = True

        def convert(obj):
            return f"{obj.street},{obj.city}"

class Person(BaseModel):
    uuid: str
    name: str
    address: Address

    @field_validator('address', mode="before")
    def validate_address(cls, v):
        if isinstance(v, Address):
            return v
        street, city = v.split(',')
        return Address(street=street, city=city)

db = DataBase()

person = Person(
    uuid=str(uuid4()),
    name="Bob",
    address=Address(street="456 Oak Ave", city="Hamburg")
)
db.add("Persons", person)

# The address is stored as a string, not a foreign key
# But when retrieved, it's reconstructed as an Address object
for p in db("Persons"):
    print(f"{p.name}: {p.address.city}")
```

## FailSafeDataBase: Error Recovery

The `FailSafeDataBase` context manager automatically creates a database snapshot if an exception occurs:

```python
from pydantic_sqlite import FailSafeDataBase
from pydantic import BaseModel
from uuid import uuid4

class User(BaseModel):
    uuid: str
    username: str

with FailSafeDataBase("users.db", snapshot_suffix="_snapshot.db") as db:
    user1 = User(uuid=str(uuid4()), username="alice")
    db.add("Users", user1)
    
    user2 = User(uuid=str(uuid4()), username="bob")
    db.add("Users", user2)
    
    # If an exception occurs here, a snapshot is automatically saved
    # as users_snapshot.db
    if True:  # Some error condition
        raise Exception("Something went wrong!")
```

After running this, you'll have:
- `users.db` - The original database
- `users_snapshot.db` - A snapshot with the data as it was before the exception

If you run the script again and an error occurs, the snapshot file is incremented to `users_snapshot(1).db`.
