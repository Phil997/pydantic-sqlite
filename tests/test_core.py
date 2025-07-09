from pydantic_sqlite import DataBase

from ._helper import Car


def test_value_in_table_with_alternative_pk(sample_db: DataBase):
    car = Car(series_number="1234", model="Volkswagen Golf")
    sample_db.add("Cars", car, pk='series_number')

    lst = [c for c in sample_db("Cars")]
    assert lst == [Car(series_number='1234', model='Volkswagen Golf')]

    assert sample_db.value_in_table('Cars', car, pk='series_number') is True
    assert sample_db.value_in_table('Cars', car.series_number, pk='series_number') is True
