import importlib
import json
import os
import sqlite3
import typing
from typing import Any, Generator, List

from pydantic import BaseModel, root_validator
from sqlite_utils import Database as _Database

from ._misc import remove_file


class TableBaseModel(BaseModel):
    table: str
    moduleclass: Any
    modulename: str
    pks: List[str]

    @root_validator(pre=True)
    def extract_modulename(cls, values):
        v = values['moduleclass']
        values.update(
            {'modulename': str(v).split("<class '")[1].split("'>")[0]})
        return values

    def data(self):
        return dict(
            table=self.table,
            modulename=self.modulename,
            pks=self.pks)


class DataBase():

    def __init__(self, **kwargs):
        self._basemodels = {}
        self._db = _Database(memory=True)

    def __call__(self, tablename) -> Generator[BaseModel, None, None]:
        """returns a Generator for all values in the Table. The returned values are subclasses of pydantic.BaseModel"""
        try:
            basemodel = self._basemodels[tablename]
            foreign_refs = {key.column: key.other_table for key in self._db[tablename].foreign_keys}
        except KeyError:
            raise KeyError(f"can not find Table: {tablename} in Database") from None
        for row in self._db[tablename].rows:
            yield self._build_basemodel_from_json(basemodel, row, foreign_refs)

    def add(self, tablename: str, value: BaseModel, pk: str = "uuid", foreign_tables={}) -> None:
        """adds a new value to the table tablename"""

        # unkown Tablename -> means new Table -> update the table_basemodel_ref list
        if tablename not in self._basemodels:
            self._basemodels_add_model(table=tablename, moduleclass=value.__class__, pks=[pk])

        # check whether the value matches the basemodels in the table
        if x := not self._basemodels[tablename].moduleclass == type(value):
            raise ValueError(f"Can not add type '{type(value)}' to the table '{tablename}', which contains values of type '{x}'")

        # create dict for writing to the Table
        data_for_save = value.__dict__ if not hasattr(value, "sqlite_repr") else value.sqlite_repr
        foreign_keys = []
        for field_name, field in value.__fields__.items():
            field_value = getattr(value, field_name)
            field_class = field_value.__class__
            special_insert = field_class.SQConfig.special_insert if hasattr(field_class, 'SQConfig') else False

            if special_insert:  # Special Insert with SQConfig.convert
                data_for_save[field_name] = field_class.SQConfig.convert(field_value)
            elif typing.get_origin(field.type_):  # Field is of Type typing
                if field.type_.__origin__ is typing.Literal:
                    data_for_save[field_name] = str(field_value)
            elif issubclass(field.type_, BaseModel):  # Field is of BaseModel
                # the value has got a field which is of type BaseModel, so this filed must be in a foreign table
                # if the field is already in the Table it continues, but if is it not in the table it will add this to the table
                # !recursive call to self.add

                if x := field_name not in foreign_tables.keys():
                    keys = list(foreign_tables.keys())
                    raise KeyError(f"detect field of Type BaseModel, but can not find '{x}' in foreign_tables (Keys: {keys})") from None
                else:
                    foreign_table_name = foreign_tables[field_name]

                if x := foreign_table_name not in self._db.table_names():
                    raise KeyError(f"Can not add a value, which has a foreign Key '{foreign_tables}' to a Table '{x}' which does not exists")

                if not self.value_in_table(foreign_table_name, field_value):
                    # the nested BaseModel is not in the foreign Table and has to be added
                    # A previously performed query ensures that the foreign table exists to which the foreign_value is to be added. 
                    # The foreign keys of this table are needed to add the nested base model object.
                    foreign_refs = {
                        key.column: key.other_table for key in self._db.table(foreign_table_name).foreign_keys}
                    self.add(foreign_table_name, field_value, "uuid", foreign_refs)

                data_for_save[field_name] = field_value.uuid
                foreign_keys.append((field_name, foreign_table_name, "uuid"))  # ignore=True

        self._db[tablename].upsert(data_for_save, pk=pk, foreign_keys=foreign_keys)

    def uuid_in_table(self, tablename: str, uuid: str) -> bool:
        """checks if the given uuid is used as a primary key in the table"""
        hits = [row for row in self._db[tablename].rows_where("uuid = ?", [uuid])]
        if len(hits) > 1:
            raise Exception("uuid is two times in table")  # TODO choice correct exceptiontype
        return False if not hits else True

    def value_in_table(self, tablename: str, value: BaseModel) -> bool:
        """checks if the given value is in the table"""
        return self.uuid_in_table(tablename, value.uuid)

    def value_from_table(self, tablename: str, uuid: str) -> Any:
        """searchs the Objekt with the given uuid in the table and returns it. Returns a subclass of type pydantic.BaseModel"""
        hits = [row for row in self._db[tablename].rows_where("uuid = ?", [uuid])]
        if len(hits) > 1:
            raise Exception("uuid is two times in table")  # TODO choice correct exceptiontype
 
        model = self._basemodels[tablename]
        foreign_refs = {key.column: key.other_table for key in self._db[tablename].foreign_keys}
        return None if not hits else self._build_basemodel_from_json(model, hits[0], foreign_refs=foreign_refs)

    def values_in_table(self, tablename) -> int:
        """returns the number of values in the Table"""
        return self._db[tablename].count

    def load(self, filename) -> None:
        """loads all data from the given file and adds them to the in-memory database"""
        if not os.path.isfile(filename):
            raise FileNotFoundError(f"Can not load {filename}")
        file_db = sqlite3.connect(filename)
        query = "".join(line for line in file_db.iterdump())
        self._db.conn.executescript(query)
        file_db.close()

        for model in self._db["__basemodels__"].rows:
            classname = model['modulename'].split('.')[-1]
            modulename = '.'.join(model['modulename'].split('.')[:-1])
            my_module = importlib.import_module(modulename)
            self._basemodels_add_model(
                table=model['table'],
                moduleclass=getattr(my_module, classname),
                pks=json.loads(model['pks']))

    def save(self, filename) -> None:
        """saves alle values from the in_memory database to a file"""
        if not filename.endswith(".db"):
            filename += ".db"
        if os.path.isfile(filename):
            os.popen(f"copy {filename} {filename}_backup")

        file_db = sqlite3.connect(f"{filename}_tmp")
        query = "".join(line for line in self._db.conn.iterdump())
        file_db.executescript(query)
        file_db.close()

        os.popen(f"copy {filename}_tmp {filename}").close()
        remove_file(f"{filename}_tmp")
        remove_file(f"{filename}_backup")

    def _basemodels_add_model(self, **kwargs):
        model = TableBaseModel(**kwargs)
        self._basemodels.update({kwargs['table']: model})
        self._db["__basemodels__"].upsert(model.data(), pk="modulename")

    def _build_basemodel_from_json(self, basemodel, row: dict, foreign_refs):
        d = {}
        for col_name, value in row.items():
            if col_name in foreign_refs.keys():
                foreign_value = self.value_from_table(foreign_refs[col_name], value)
                d.update({col_name: foreign_value})
            else:
                d.update({col_name: value})
        return basemodel.moduleclass(**d)
