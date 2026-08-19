# Welcome to **pydantic-sqlite**!

`pydantic-sqlite` makes it easy to store Pydantic models directly in a SQLite database and retrieve fully-typed objects -> no manual serialization.

`pydantic-sqlite` bridges the gap between Pydantic models and SQLite persistence. Instead of manually mapping your models to database columns or writing SQL, you work directly with your Pydantic BaseModel instances. The library automatically handles serialization and deserialization. You can store BaseModel instancea directly in the database, and when querying, you always get back fully reconstructed, ready-to-use Pydantic objects—just like your originals.

## Key Features

- **Seamless Model Storage** - Store Pydantic `BaseModel` directly in SQLite
- **Nested Model Support** - Automatically handle foreign key relationships between models
- **Flexible Primary Keys** - Use any field as primary key (defaults to `uuid`)
- **Complex Type Handling** - Support for lists, unions, and custom type conversions
- **Type Safety** - Retrieved objects are fully reconstructed as their original Pydantic models
- **Simple Query API** - Intuitive interface for adding and querying data
- **Row Deletion** - Remove single rows by primary key or bulk delete with WHERE clauses
- **Error Recovery** - Optional `FailSafeDataBase` context manager for automatic snapshots on exceptions

## Quick Example

```python
from pydantic import BaseModel
from pydantic_sqlite import DataBase

class Person(BaseModel):
    uuid: str
    name: str
    age: int

# Create database and add model
db = DataBase()
person = Person(uuid="1", name="Alice", age=30)
db.add("Persons", person)

# Query and retrieve
for person in db("Persons"):
    print(f"{person.name} is {person.age} years old")
```

## Getting Started

Follow the [Basic Usage](basic-usage.md) guide for installation and your first database.

For more examples and use cases, check out [Advanced Usage](advanced-usage.md) and [Examples](examples.md).

### Installation

**Using pip:**
```bash
pip install pydantic-sqlite
```

**Using uv:**
```bash
uv add pydantic-sqlite
```

**Using poetry:**
```bash
poetry add pydantic-sqlite
```

## Documentation

- **[Basic Usage](basic-usage.md)** - Installation, core features and common patterns (add, query, update, delete)
- **[Advanced Usage](advanced-usage.md)** - Nested models, cascading deletes, custom configurations, and complex scenarios
- **[Examples](examples.md)** - Complete, runnable code examples


## Support

- **GitHub**: [Phil997/pydantic-sqlite](https://github.com/Phil997/pydantic-sqlite)
- **Issues**: [Report bugs or request features](https://github.com/Phil997/pydantic-sqlite/issues)

## License

MIT – See [LICENSE](https://github.com/Phil997/pydantic-sqlite/blob/main/LICENSE) for details.
