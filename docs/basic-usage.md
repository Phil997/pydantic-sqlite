# Basic Usage

## Adding Models

```python
from pydantic import BaseModel
from pydantic_sqlite import DataBase

class Product(BaseModel):
    uuid: str
    name: str
    price: float
    in_stock: bool

db = DataBase()

# Create and add a product
product = Product(
    uuid="prod-001",
    name="Laptop",
    price=999.99,
    in_stock=True
)
db.add("Products", product)

# Add more products
db.add("Products", Product(uuid="prod-002", name="Mouse", price=29.99, in_stock=True))
db.add("Products", Product(uuid="prod-003", name="Keyboard", price=79.99, in_stock=False))
```

## Querying Models

### Querying all entries

```python
# Iterate through all products
for product in db("Products"):
    status = "Available" if product.in_stock else "Out of stock"
    print(f"{product.name}: ${product.price} ({status})")
```

### Querying with Conditions

Use the `where` parameter to filter results:

```python
# Get all products in stock
for product in db("Products", where="in_stock = :stock", where_args={"stock": True}):
    print(f"{product.name} is available")

# Get products over $50
for product in db("Products", where="price > :min_price", where_args={"min_price": 50}):
    print(f"{product.name}: ${product.price}")

# Complex queries
for product in db(
    "Products",
    where="price > :min_price AND in_stock = :stock",
    where_args={"min_price": 50, "stock": True}
):
    print(product.name)
```

## Primitive Datatypes

pydantic-sqlite supports all common Python types. Here's a comprehensive example with all basic primitive types:

```python
from typing import Optional
from pydantic import BaseModel
from pydantic_sqlite import DataBase

class DataExample(BaseModel):
    uuid: str
    name: str
    count: int
    rating: float
    active: bool
    description: Optional[str] = None
    notes: Optional[str] = None
    categories: list[str]

db = DataBase()

# Add one example with all fields
db.add("Examples", DataExample(
    uuid="ex-1",
    name="Complete Example",
    count=42,
    rating=4.5,
    active=True,
    description="A complete entry",
    notes=None,  # This optional field is None
    categories=["python", "database", "tutorial"]
))

# Retrieve and verify all types
for item in db("Examples"):
    assert isinstance(item.uuid, str)
    assert isinstance(item.name, str)
    assert isinstance(item.count, int)
    assert isinstance(item.rating, float)
    assert isinstance(item.active, bool)
    assert isinstance(item.categories, list)
    # Optional fields can be None or their type
    assert item.notes is None
    assert item.description == "A complete entry"
    
    print(f"{item.name}: {item.rating}★")
    print(f"  Description: {item.description}")
    print(f"  Categories: {', '.join(item.categories)}")
```

## Supported Field Types

The following field types are supported and can be stored and loaded through a Pydantic model:

| Field type | Notes |
| --- | --- |
| `str`, `int`, `float`, `bool` | Stored as SQLite scalar values |
| `datetime`, `Decimal` | Serialized by `sqlite-utils` |
| `Optional[T]` | Supports `None` values |
| `Union[...]` | Reconstructed using the first matching type |
| `Literal[...]` | Stored as a string |
| `list[T]` | Primitive values are stored as JSON |
| `tuple[T, ...]` | Stored as JSON and reconstructed as a tuple |
| `set[T]` | Stored as JSON and reconstructed as a set |
| `dict[K, V]` | Primitive values are stored as JSON |
| `Enum` and `StrEnum` | The Enum value is stored and the Enum member is reconstructed |
| Nested `BaseModel` | Requires a corresponding `foreign_tables` entry; see [Nested Models](advanced-usage.md#nested-models-with-foreign-keys) |

`Any` is also supported for storage. Since it carries no concrete type information, an Enum stored through an `Any` field is loaded as its value rather than as an Enum member. Enum fields should therefore be explicitly typed when the Enum type must be preserved.

## Enum Values

Enum fields are stored using their values and reconstructed as Enum members when queried:

```python
from enum import Enum
from pydantic import BaseModel
from pydantic_sqlite import DataBase

class Status(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class User(BaseModel):
    uuid: str
    name: str
    status: Status

db = DataBase()
db.add("Users", User(uuid="user-1", name="Alice", status=Status.ACTIVE))

user = db.model_from_table("Users", "user-1")
assert user.status is Status.ACTIVE
assert isinstance(user.status, Status)
```

The same behavior applies to Enum fields with integer values, such as `class Priority(Enum): LOW = 1`.

## Updating Data

`pydantic-sqlite` uses an "upsert" strategy. If you add a model with the same primary key, it updates the existing entry:

```python
from pydantic import BaseModel
from pydantic_sqlite import DataBase

class User(BaseModel):
    uuid: str
    username: str
    email: str

db = DataBase()

# Initial user
user = User(uuid="user-1", username="alice", email="alice@example.com")
db.add("Users", user)

# Update: add the same UUID with new data
updated_user = User(uuid="user-1", username="alice", email="alice.new@example.com")
db.add("Users", updated_user)

# Only one entry with uuid="user-1", with the new email
for user in db("Users"):
    print(user.email)  # alice.new@example.com
```

## Checking for Existence

```python
# Check by primary key value (uuid)
if db.model_in_table("Users", "user-1"):
    print("User exists")

# Check by model instance
if db.model_in_table("Users", user):
    print("Alice is in the database")

# Get a specific model by uuid
user = db.model_from_table("Users", "user-1")
if user:
    print(f"Found: {user.username}")
```

## Deleting Data

Remove rows from the database with `delete` and `delete_where`:

```python
from pydantic import BaseModel
from pydantic_sqlite import DataBase

class Product(BaseModel):
    uuid: str
    name: str
    in_stock: bool

db = DataBase()

laptop = Product(uuid="prod-001", name="Laptop", in_stock=True)
db.add("Products", laptop)
db.add("Products", Product(uuid="prod-002", name="Mouse", in_stock=True))
db.add("Products", Product(uuid="prod-003", name="Keyboard", in_stock=False))

# Delete all rows matching a condition -> number of removed rows
removed = db.delete_where("Products", where="in_stock = :stock", where_args={"stock": False})
print(removed)  # 1 (the Keyboard)

# Delete a single row by primary key -> True if the row was deleted
deleted = db.delete("Products", "prod-001")
print(deleted)  # True

# Delete by model instance (the primary key is extracted automatically)
deleted = db.delete("Products", laptop)
print(deleted)  # False - the Laptop row was already deleted above

# Un-deleted rows are still there
for product in db("Products"):
    print(product.name)  # Mouse
```

`delete` and `delete_where` raise a `KeyError` if the table does not exist.

Note: deleting only removes rows from the specified table. Rows in foreign tables that are referenced by nested models are kept. See [Cascading Deletes](advanced-usage.md#cascading-deletes) to delete nested rows as well.

## Persisting to Disk

By default, `DataBase()` creates an in-memory database. To save data to a file:

```python
from pydantic_sqlite import DataBase

# Create a database backed by a file
db = DataBase("my_database.db")

# ... add and query data ...

# Save to disk
db.save("my_database.db")
```

Or load an existing database:

```python
db = DataBase("my_database.db")

# The database file is automatically loaded if it exists
for person in db("Persons"):
    print(person)
```
