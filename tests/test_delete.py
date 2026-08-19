import pytest

from pydantic_sqlite import DataBase

from ._helper import Car, Employee, Garage, Person


def _count_rows(db: DataBase, tablename: str) -> int:
    query = f"SELECT COUNT(*) FROM '{tablename}'"
    return db._db.conn.execute(query).fetchone()[0]


def _row_exists(db: DataBase, tablename: str, column: str, value: str) -> bool:
    query = f"SELECT COUNT(*) FROM '{tablename}' WHERE {column} = ?"
    return db._db.conn.execute(query, (value,)).fetchone()[0] > 0


def _column_values(db: DataBase, tablename: str, column: str) -> list[str]:
    query = f"SELECT {column} FROM '{tablename}' ORDER BY {column}"
    return [row[0] for row in db._db.conn.execute(query)]


def test_delete_by_primary_key():
    db = DataBase()
    person = Person(uuid="1234", name="Test User")
    db.add("Persons", person)

    assert db.delete("Persons", "1234") is True
    assert _count_rows(db, "Persons") == 0
    assert _row_exists(db, "Persons", "uuid", "1234") is False


def test_delete_by_basemodel():
    db = DataBase()
    person = Person(uuid="1234", name="Test User")
    db.add("Persons", person)

    assert db.delete("Persons", person) is True
    assert _count_rows(db, "Persons") == 0


def test_delete_not_found():
    db = DataBase()
    person = Person(uuid="1234", name="Test User")
    db.add("Persons", person)

    assert db.delete("Persons", "unknown") is False
    assert _count_rows(db, "Persons") == 1
    assert _column_values(db, "Persons", "uuid") == ["1234"]


def test_delete_not_existing_table():
    db = DataBase()
    with pytest.raises(KeyError, match="Can't find table 'Unknown' in Database"):
        db.delete("Unknown", "1234")


def test_delete_alternative_primary_key():
    db = DataBase()
    car = Car(series_number="1234", model="Volkswagen Golf")
    db.add("Cars", car, pk="series_number")

    assert db.delete("Cars", car) is True
    assert _count_rows(db, "Cars") == 0
    assert _row_exists(db, "Cars", "series_number", "1234") is False


def test_delete_where():
    db = DataBase()
    db.add("Persons", Person(uuid="1", name="unitest"))
    db.add("Persons", Person(uuid="2", name="unitest"))
    db.add("Persons", Person(uuid="3", name="other"))

    assert db.delete_where("Persons", where="name = :name", where_args={"name": "unitest"}) == 2
    assert _column_values(db, "Persons", "uuid") == ["3"]


def test_delete_where_no_match():
    db = DataBase()
    db.add("Persons", Person(uuid="1", name="unitest"))

    assert db.delete_where("Persons", where="name = :name", where_args={"name": "unknown"}) == 0
    assert _count_rows(db, "Persons") == 1
    assert _column_values(db, "Persons", "uuid") == ["1"]


def test_delete_where_not_existing_table():
    db = DataBase()
    with pytest.raises(KeyError, match="Can't find table 'Person' in Database"):
        db.delete_where("Person", where="name = :name", where_args={"name": "unitest"})


def test_delete_no_cascade_for_nested():
    db = DataBase()
    person = Person(uuid="p1", name="unitest")
    employee = Employee(uuid="e1", person=person)
    db.add("Persons", person)
    db.add("Employees", employee, foreign_tables={"person": "Persons"})

    assert db.delete("Employees", "e1") is True
    assert _count_rows(db, "Employees") == 0
    assert _count_rows(db, "Persons") == 1
    assert _column_values(db, "Persons", "uuid") == ["p1"]


def test_delete_cascade_nested():
    db = DataBase()
    person = Person(uuid="p1", name="unitest")
    employee = Employee(uuid="e1", person=person)
    db.add("Persons", person)
    db.add("Employees", employee, foreign_tables={"person": "Persons"})

    assert db.delete("Employees", "e1", cascade=True) is True
    assert _count_rows(db, "Employees") == 0
    assert _count_rows(db, "Persons") == 0
    assert _row_exists(db, "Persons", "uuid", "p1") is False


def test_delete_cascade_shared_reference():
    db = DataBase()
    person = Person(uuid="p1", name="unitest")
    employee1 = Employee(uuid="e1", person=person)
    employee2 = Employee(uuid="e2", person=person)
    db.add("Persons", person)
    db.add("Employees", employee1, foreign_tables={"person": "Persons"})
    db.add("Employees", employee2, foreign_tables={"person": "Persons"})

    assert db.delete("Employees", "e1", cascade=True) is True
    assert _count_rows(db, "Persons") == 1
    assert _column_values(db, "Persons", "uuid") == ["p1"]

    assert db.delete("Employees", "e2", cascade=True) is True
    assert _count_rows(db, "Persons") == 0


def test_delete_cascade_nested_list():
    db = DataBase()
    car1 = Car(series_number="s1", model="Volkswagen Golf")
    car2 = Car(series_number="s2", model="Audi A4")
    garage = Garage(uuid="g1", cars=[car1, car2])
    db.add("Cars", car1, pk="series_number")
    db.add("Cars", car2, pk="series_number")
    db.add("Garages", garage, foreign_tables={"cars": "Cars"})

    assert db.delete("Garages", "g1", cascade=True) is True
    assert _count_rows(db, "Garages") == 0
    assert _count_rows(db, "Cars") == 0
    assert _column_values(db, "Cars", "series_number") == []


def test_delete_where_cascade():
    db = DataBase()
    person = Person(uuid="p1", name="unitest")
    employee = Employee(uuid="e1", person=person)
    db.add("Persons", person)
    db.add("Employees", employee, foreign_tables={"person": "Persons"})

    assert db.delete_where("Employees", where="uuid = :uuid", where_args={"uuid": "e1"}, cascade=True) == 1
    assert _count_rows(db, "Employees") == 0
    assert _count_rows(db, "Persons") == 0
    assert _row_exists(db, "Persons", "uuid", "p1") is False
