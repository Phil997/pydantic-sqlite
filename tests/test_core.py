import pytest

from pydantic_sqlite import DataBase

from ._helper import Car, Employee, Person


def test_add_3_items(sample_db: DataBase):
    sample_db.add("Humans", Person(uuid="1234", name="Han Solo"), pk='uuid')
    sample_db.add("Humans", Person(uuid="5678", name="Darth Vader"), pk='uuid')
    sample_db.add("Humans", Person(uuid="abcd", name="Yoda"), pk='uuid')

    print(sample_db.values_in_table("Humans"))


def test_value_in_table_with_alternative_pk(sample_db: DataBase):
    car = Car(series_number="1234", model="Volkswagen Golf")
    sample_db.add("Cars", car, pk='series_number')

    lst = [c for c in sample_db("Cars")]
    assert lst == [Car(series_number='1234', model='Volkswagen Golf')]

    assert sample_db.value_in_table('Cars', car, pk='series_number') is True
    assert sample_db.value_in_table('Cars', car.series_number, pk='series_number') is True


def test_exception_unkwon_table(sample_db: DataBase):

    with pytest.raises(KeyError, match="Can't find table 'UnknownTable' in Database"):
        for _ in sample_db("UnknownTable"):
            ...


def test_exception_wrong_type(sample_db: DataBase):
    person = Person(uuid="abc", name="unitest")

    with pytest.raises(
            TypeError,
            match="Only pydantic BaseModels can be added to the database"):
        sample_db.add("MyTable", 1)

    sample_db.add("MyTable", person)

    with pytest.raises(
            TypeError,
            match="Only pydantic BaseModels of type 'Person' can be added to the table 'MyTable'"):
        sample_db.add("MyTable", "string")


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
