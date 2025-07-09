import pytest

from pydantic_sqlite import DataBase

from ._helper import Car


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

