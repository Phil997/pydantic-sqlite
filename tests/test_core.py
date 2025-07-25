import pytest

from pydantic_sqlite import DataBase

from ._helper import Address, Car, Employee, Person


def test_add():
    db = DataBase()
    person = Person(uuid="1234", name="Test User")
    db.add("Persons", person)

    assert db.model_in_table('Persons', person)
    assert db.model_in_table('Persons', person.uuid)

    for x in db('Persons'):
        assert isinstance(x, Person)


def test_add_3_items():
    db = DataBase()
    db.add("Humans", Person(uuid="1234", name="Han Solo"), pk='uuid')
    db.add("Humans", Person(uuid="5678", name="Darth Vader"), pk='uuid')
    db.add("Humans", Person(uuid="abcd", name="Yoda"), pk='uuid')

    assert db.count_entries_in_table("Humans") == 3


def test_alternative_primary_key(sample_db: DataBase):
    car = Car(series_number="1234", model="Volkswagen Golf")
    sample_db.add("Cars", car, pk='series_number')

    lst = [c for c in sample_db("Cars")]
    assert lst == [Car(series_number='1234', model='Volkswagen Golf')]

    assert sample_db.model_in_table('Cars', car) is True
    assert sample_db.model_in_table('Cars', car.series_number) is True


def test_no_model_mix_allowed_in_table():
    """
    Test that only models of the same type can be added to a table.
    """
    db = DataBase()
    person = Person(uuid="1234", name="Test User")
    address = Address(uuid="5678", street="Main St", city="Springfield", zip_code="12345")

    db.add("MyTable", person)
    with pytest.raises(TypeError):
        db.add("MyTable", address)


def test_exception_unkwon_table():
    with pytest.raises(KeyError, match="Can't find table 'UnknownTable' in Database"):
        for _ in DataBase()("UnknownTable"):
            ...


def test_exception_wrong_type():
    db = DataBase()
    person = Person(uuid="abc", name="unitest")
    address = Address(uuid="lkj", street="Main St", city="Springfield", zip_code="12345")

    with pytest.raises(
            TypeError,
            match="Only pydantic BaseModels can be added to the database"):
        db.add("MyTable", 1)

    db.add("MyTable", person)

    with pytest.raises(
            TypeError,
            match="Only pydantic BaseModels of type 'Person' can be added to the table 'MyTable'"):
        db.add("MyTable", address)


def test_get_check_foreign_table_name_success(sample_db: DataBase):
    person = Person(uuid="abc", name="unitest")
    employee = Employee(uuid="xyz", person=person)
    sample_db.add("Humans", person)
    sample_db.add("Employee", employee, foreign_tables={"person": "Humans"})

    tablename = sample_db._get_foreign_table_name("person", {"person": "Humans"})
    assert tablename == "Humans"


def test_get_foreign_table_name_missing_field(sample_db: DataBase):
    person = Person(uuid="abc", name="unitest")
    employee = Employee(uuid="xyz", person=person)
    sample_db.add("Humans", person)
    sample_db.add("Employee", employee, foreign_tables={"person": "Humans"})

    with pytest.raises(KeyError, match="detect field of Type BaseModel, but can not find 'field'"):
        sample_db._get_foreign_table_name("field", {"other_field": "Humans"})


def test_get_foreign_table_name_missing_table(sample_db: DataBase):
    person = Person(uuid="abc", name="unitest")
    employee = Employee(uuid="xyz", person=person)
    sample_db.add("Humans", person)
    sample_db.add("Employee", employee, foreign_tables={"person": "Humans"})

    with pytest.raises(KeyError, match="to a Table 'NonExistentTable' which does not exists"):
        sample_db._get_foreign_table_name("field", {"field": "NonExistentTable"})
