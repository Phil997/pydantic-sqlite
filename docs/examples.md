# Examples

Complete, runnable code examples for different use cases.

## Example 1: Simple Contact List

A basic example showing CRUD operations with a simple model.

**What's happening here:**

- We define a Pydantic model `Contact` with `contact_id` as the unique identifier
- Since the model doesn't have a `uuid` field, we tell pydantic-sqlite to use `contact_id` as the primary key with `pk="contact_id"`
- When we query the database, we get back `Contact` objects, not raw dictionaries
- Updating is simple: add the same ID with new data (upsert)
- The data persists to a file with `save()`

```python
from pydantic import BaseModel
from pydantic_sqlite import DataBase

class Contact(BaseModel):
    contact_id: str
    name: str
    email: str
    phone: str

# Create database
db = DataBase("contacts.db")

# Create contacts
contacts = [
    Contact(contact_id="1", name="Alice", email="alice@example.com", phone="555-0001"),
    Contact(contact_id="2", name="Bob", email="bob@example.com", phone="555-0002"),
    Contact(contact_id="3", name="Charlie", email="charlie@example.com", phone="555-0003"),
]

# Add all contacts (specify pk since Contact doesn't have 'uuid' field)
for contact in contacts:
    db.add("Contacts", contact, pk="contact_id")

# Display all contacts - they're reconstructed as Contact instances
print("All Contacts:")
for contact in db("Contacts"):
    print(f"  {contact.name}: {contact.email}")

# Update a contact - upsert with same contact_id replaces old entry
updated = Contact(contact_id="1", name="Alice Smith", email="alice.smith@example.com", phone="555-0001")
db.add("Contacts", updated, pk="contact_id")

# Query specific contact by primary key
alice = db.model_from_table("Contacts", "1")
print(f"\nUpdated: {alice.name}")  # Output: Updated: Alice Smith

# Save to disk
db.save("contacts.db")
```

## Example 2: Blog with Posts and Tags

A more complex example with nested models and relationships.

**What's happening here:**

- `Tag` objects are stored in a separate "Tags" table with `pk="tag_id"`
- `Post` objects are stored in a "Posts" table with `pk="post_id"`
- The `tags: list[Tag]` field in Post creates a foreign key relationship
- When we retrieve a Post, pydantic-sqlite automatically reconstructs its tags from the Tags table
- This is real database normalization: related data in separate tables with automatic reconstruction


```python
from pydantic import BaseModel
from pydantic_sqlite import DataBase
from datetime import datetime

class Tag(BaseModel):
    tag_id: str
    name: str
    slug: str

class Post(BaseModel):
    post_id: str
    title: str
    content: str
    author: str
    tags: list[Tag]
    created_at: str

db = DataBase("blog.db")

# Create tags
tags = [
    Tag(tag_id="py", name="Python", slug="python"),
    Tag(tag_id="db", name="Database", slug="database"),
    Tag(tag_id="web", name="Web", slug="web"),
]

# Add tags to database (specify pk="tag_id" since Tag doesn't have uuid)
for tag in tags:
    db.add("Tags", tag, pk="tag_id")

# Create posts with tags (tags are nested models)
posts = [
    Post(
        post_id="1",
        title="Getting Started with pydantic-sqlite",
        content="This is a comprehensive guide...",
        author="Alice",
        tags=[tags[0], tags[1]],  # Python, Database tags
        created_at=str(datetime.now())
    ),
    Post(
        post_id="2",
        title="Web Development Tips",
        content="10 tips for better web apps...",
        author="Bob",
        tags=[tags[2]],  # Web tag
        created_at=str(datetime.now())
    ),
]

# Add posts with foreign key reference to tags table
# This creates relationships: Post.tags → Tags table
for post in posts:
    db.add("Posts", post, pk="post_id", foreign_tables={"tags": "Tags"})

# Retrieve and display - tags are automatically reconstructed from the Tags table
print("Blog Posts:")
for post in db("Posts"):
    tag_names = ", ".join([tag.name for tag in post.tags])
    print(f"  {post.title} by {post.author}")
    print(f"    Tags: {tag_names}\n")

# Query by author
print("Posts by Alice:")
for post in db("Posts"):
    if post.author == "Alice":
        print(f"  - {post.title}")

db.save("blog.db")
```

## Example 3: Multi-level Nesting with Custom Primary Keys

Complex relationships with different primary keys at each level.

**What's happening here:**

- Three separate tables: Wheels, Engines, Cars (each with its own primary key field)
- Car has TWO nested relationships: single Engine and list of Wheels
- `foreign_tables={"engine": "Engines", "wheels": "Wheels"}` tells pydantic-sqlite how to reconstruct both
- When we fetch a Car, both the engine object AND the entire wheel list are reconstructed from their tables
- This demonstrates real-world complexity: multi-level relationships with different PK strategies

```python
from pydantic import BaseModel
from pydantic_sqlite import DataBase

class Wheel(BaseModel):
    batch_number: str
    diameter: int
    width: int

class Engine(BaseModel):
    engine_id: str
    type: str
    horsepower: int

class Car(BaseModel):
    vin: str
    brand: str
    model: str
    year: int
    engine: Engine
    wheels: list[Wheel]

db = DataBase("cars.db")

# Add wheels first (pk="batch_number")
wheels = [
    Wheel(batch_number="W001", diameter=18, width=8),
    Wheel(batch_number="W002", diameter=18, width=8),
    Wheel(batch_number="W003", diameter=18, width=8),
    Wheel(batch_number="W004", diameter=18, width=8),
]

for wheel in wheels:
    db.add("Wheels", wheel, pk="batch_number")

# Add engines (pk="engine_id")
engine = Engine(engine_id="E001", type="V6", horsepower=300)
db.add("Engines", engine, pk="engine_id")

# Add car with TWO different nested relationships
car = Car(
    vin="1G1ZT52806F109149",
    brand="Chevrolet",
    model="Corvette",
    year=2024,
    engine=engine,
    wheels=wheels
)

# Specify foreign_tables for BOTH relationships
db.add(
    "Cars",
    car,
    pk="vin",
    foreign_tables={"engine": "Engines", "wheels": "Wheels"}
)

# Retrieve - full object hierarchy is reconstructed
for c in db("Cars"):
    print(f"{c.year} {c.brand} {c.model} (VIN: {c.vin})")
    print(f"  Engine: {c.engine.type} ({c.engine.horsepower} hp)")
    print(f"  Wheels: {len(c.wheels)} x {c.wheels[0].diameter}\" ({c.wheels[0].width}\" width)")

db.save("cars.db")
```

## Example 4: Using FailSafeDataBase for Error Recovery

Automatic snapshots when errors occur.

**What's happening here:**

- `FailSafeDataBase` is a context manager that wraps the normal `DataBase`
- If ANY exception occurs during the `with` block, a snapshot is automatically saved
- The snapshot filename is `transactions_snapshot.db` (customizable with `snapshot_suffix`)
- You can use this to recover partial state if your transaction processing crashes
- Without FailSafeDataBase, you'd lose unsaved changes on error

```python
from pydantic import BaseModel
from pydantic_sqlite import FailSafeDataBase
from uuid import uuid4

class Transaction(BaseModel):
    transaction_id: str
    amount: float
    description: str
    status: str

def process_transaction(amount, description):
    # FailSafeDataBase automatically creates snapshots if exceptions occur
    with FailSafeDataBase("transactions.db") as db:
        # Create new transaction
        transaction = Transaction(
            transaction_id=str(uuid4()),
            amount=amount,
            description=description,
            status="pending"
        )
        # Specify pk since Transaction doesn't have 'uuid' field
        db.add("Transactions", transaction, pk="transaction_id")
        
        # Simulate some processing
        if amount < 0:
            raise ValueError("Amount must be positive")
        
        # Update status (upsert with same transaction_id)
        transaction.status = "completed"
        db.add("Transactions", transaction, pk="transaction_id")
        
        print(f"Processed: {transaction.transaction_id}")

# This will fail and create a snapshot
try:
    process_transaction(-100, "Invalid transaction")
except ValueError as e:
    print(f"Error: {e}")
    print("A snapshot was automatically saved to 'transactions_snapshot.db'")

# Successful transaction
process_transaction(100, "Valid transaction")
print("Transaction completed successfully")
```

## Example 5: Using SQConfig for Custom Storage

**What's happening here:**

- Normally nested BaseModels get their own tables (foreign keys)
- With `SQConfig` and `special_insert=True`, we store the object as a string instead
- The `convert()` method defines how to serialize the object (Coordinates → "52.52,13.40")
- The `@field_validator` with `mode="before"` defines how to deserialize it back
- Use this when you don't need the nested object queryable separately (small objects, metadata)


Storing nested objects as strings instead of separate tables.

```python
from pydantic import BaseModel, field_validator
from pydantic_sqlite import DataBase
from uuid import uuid4

class Coordinates(BaseModel):
    latitude: float
    longitude: float

    class SQConfig:
        special_insert: bool = True

        @staticmethod
        def convert(obj):
            # Store as comma-separated string instead of a separate table
            return f"{obj.latitude},{obj.longitude}"

class Location(BaseModel):
    location_id: str
    name: str
    coordinates: Coordinates

    @field_validator('coordinates', mode="before")
    def parse_coordinates(cls, v):
        # When loading from DB, reconstruct Coordinates from string
        if isinstance(v, Coordinates):
            return v
        lat, lon = map(float, v.split(','))
        return Coordinates(latitude=lat, longitude=lon)

db = DataBase("locations.db")

# Create locations
locations = [
    Location(
        location_id="1",
        name="Berlin",
        coordinates=Coordinates(latitude=52.52, longitude=13.40)
    ),
    Location(
        location_id="2",
        name="Paris",
        coordinates=Coordinates(latitude=48.86, longitude=2.35)
    ),
]

for loc in locations:
    db.add("Locations", loc, pk="location_id")

# Retrieve and use - Coordinates are reconstructed from the stored string
for loc in db("Locations"):
    print(f"{loc.name}: ({loc.coordinates.latitude}, {loc.coordinates.longitude})")
    # Output: Berlin: (52.52, 13.4)
    # Output: Paris: (48.86, 2.35)

db.save("locations.db")
```

## Example 6: Querying and Filtering

**What's happening here:**

- WHERE clauses use SQLite syntax with `:parameter` placeholders
- `where_args` passes the actual values (prevents SQL injection, safer)
- Returned objects are full Student instances, not raw database rows
- You can combine conditions with AND/OR
- This is actual SQL querying, but you work with Python objects


Using WHERE clauses for advanced queries.

```python
from pydantic import BaseModel
from pydantic_sqlite import DataBase

class Student(BaseModel):
    student_id: str
    name: str
    grade: int
    gpa: float

db = DataBase("school.db")

# Add students
students = [
    Student(student_id="S001", name="Alice", grade=10, gpa=3.9),
    Student(student_id="S002", name="Bob", grade=10, gpa=3.2),
    Student(student_id="S003", name="Charlie", grade=11, gpa=3.7),
    Student(student_id="S004", name="Diana", grade=11, gpa=3.95),
]

for student in students:
    db.add("Students", student, pk="student_id")

# Simple query: grade 10 students
print("Grade 10 students:")
for student in db("Students", where="grade = :g", where_args={"g": 10}):
    print(f"  {student.name}")
    # Output: Alice, Bob

# High achievers (GPA > 3.7)
print("\nHigh achievers (GPA > 3.7):")
for student in db("Students", where="gpa > :gpa", where_args={"gpa": 3.7}):
    print(f"  {student.name} ({student.gpa})")
    # Output: Alice (3.9), Diana (3.95)

# Complex query: Grade 11 with GPA > 3.8
print("\nGrade 11 advanced students:")
for student in db(
    "Students",
    where="grade = :grade AND gpa > :gpa",
    where_args={"grade": 11, "gpa": 3.8}
):
    print(f"  {student.name}")
    # Output: Diana

# Count total
total = db.count_entries_in_table("Students")
print(f"\nTotal students: {total}")  # Output: 4

db.save("school.db")
```

## Example 7: Deleting Consumed Work-Queue Entries

**What's happening here:**

- The `Settlements` table is used as a one-time ledger: a row is created on the trade date and must be removed once the settlement matures
- `delete` removes a single row by primary key and returns `True` if the row existed, `False` otherwise
- `delete_where` removes all matching rows and returns the number of removed rows
- Re-running the workflow does not double-count matured settlements, because their rows are gone

```python
from pydantic import BaseModel
from pydantic_sqlite import DataBase

class Settlement(BaseModel):
    uuid: str
    strategy_id: str
    settlement_date: str
    cash: float

db = DataBase()

# Pending settlements - the table acts as a queue of not-yet-mature cash flows
db.add(
    "Settlements",
    Settlement(uuid="fill-123", strategy_id="momentum", settlement_date="2026-01-05", cash=1000.0),
)
db.add(
    "Settlements",
    Settlement(uuid="fill-124", strategy_id="momentum", settlement_date="2026-01-05", cash=500.0),
)
db.add(
    "Settlements",
    Settlement(uuid="fill-125", strategy_id="index", settlement_date="2026-01-05", cash=250.0),
)

# Bulk remove all matured momentum settlements -> returns the removed count
removed = db.delete_where(
    "Settlements",
    where="strategy_id = :strategy AND settlement_date <= :date",
    where_args={"strategy": "momentum", "date": "2026-01-05"},
)
print(f"Matured settlements removed: {removed}")  # Output: 2

# Remove the remaining settlement by primary key
deleted = db.delete("Settlements", "fill-125")
print(f"Settlement deleted: {deleted}")  # Output: True

# The table is now empty - nothing can be double-counted on a re-run
print(db.count_entries_in_table("Settlements"))  # Output: 0
```

Deleting only touches the given table. Pass `cascade=True` to also clean up exclusively referenced nested rows in foreign tables — see [Cascading Deletes](advanced-usage.md#cascading-deletes).
