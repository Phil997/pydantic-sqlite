# pydantic-sqlite

![Python](https://img.shields.io/badge/python-3.10%20|%203.11%20|%203.12%20|%203.13%20|%203.14-blue?logo=python&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-brightgreen.svg)
[![codecov](https://codecov.io/github/Phil997/pydantic-sqlite/graph/badge.svg?token=MCCXX7XF9V)](https://codecov.io/github/Phil997/pydantic-sqlite)

![Pydantic](https://img.shields.io/badge/pydantic-%3E%3D2.1.0-red?logo=pydantic&logoColor=white)
![SQLite](https://img.shields.io/badge/sqlite-%3E%3D3-003B57?logo=sqlite&logoColor=white)

**pydantic-sqlite** makes it easy to store Pydantic models directly in a SQLite database and retrieve fully-typed objects -> no manual serialization.

**pydantic-sqlite** bridges the gap between Pydantic models and SQLite persistence. Instead of manually mapping your models to database columns or writing SQL, you work directly with your Pydantic BaseModel instances. The library automatically handles serialization and deserialization. You can store BaseModel instancea directly in the database, and when querying, you always get back fully reconstructed, ready-to-use Pydantic objects—just like your originals.


## Documentation and Examples

For documentation, and examples, visit: **[pydantic-sqlite Documentation](https://phil997.github.io/pydantic-sqlite/)**

## Installation

**Using pip**

```bash
pip install pydantic-sqlite
```

**Using uv**

```bash
uv add pydantic-sqlite
```

**Using poetry**

```bash
poetry add pydantic-sqlite
```

## Quick Start

```python
from pydantic import BaseModel
from pydantic_sqlite import DataBase

class Person(BaseModel):
    uuid: str
    name: str
    age: int

# Create a database
db = DataBase()

# Add a person - just pass your model instance
person = Person(uuid="1", name="Alice", age=30)
db.add("Persons", person)

# Retrieve all people - you get back Person instances, not raw rows
for person in db("Persons"):
    print(f"{person.name} is {person.age} years old")
    assert isinstance(person, Person)  # ✓ True
```


## Support

- **Repository**: [GitHub](https://github.com/Phil997/pydantic-sqlite)
- **Issues**: [Report bugs or request features](https://github.com/Phil997/pydantic-sqlite/issues)

## License

MIT – See [LICENSE](LICENSE) for details.
