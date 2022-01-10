import importlib
import inspect
import json
import os
import sqlite3
import tempfile
import typing
from shutil import copyfile
from typing import Generator, List, Union

from pydantic import BaseModel, root_validator
from pydantic.fields import ModelField
from sqlite_utils import Database as _Database
from typing_inspect import is_literal_type, is_union_type

from ._misc import iterable_in_type_repr

SPECIALTYPE = [
    typing.Any, 
    typing.Literal,
    typing.Union]

class TableBaseModel(BaseModel):
    table: str
    moduleclass: typing.Any
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
            yield self._build_basemodel_from_dict(basemodel, row, foreign_refs)

    def add(self, tablename: str, value: BaseModel, foreign_tables={}, update_nested_models=True, pk: str = "uuid") -> None:
        """adds a new value to the table tablename"""

        # unkown Tablename -> means new Table -> update the table_basemodel_ref list
        if tablename not in self._basemodels:
            self._basemodels_add_model(table=tablename, moduleclass=value.__class__, pks=[pk])

        # check whether the value matches the basemodels in the table
        if not self._basemodels[tablename].moduleclass == type(value):
            raise ValueError(
                f"Can not add type '{type(value)}' to the table '{tablename}', which contains values of type '{self._basemodels[tablename].moduleclass}'")

        # create dict for writing to the Table
        data_for_save = value.dict() if not hasattr(value, "sqlite_repr") else value.sqlite_repr
        foreign_keys = []
        for field_name, field in value.__fields__.items():
            field_value = getattr(value, field_name)
            field_class = field_value.__class__

            special_insert = field_class.SQConfig.special_insert if hasattr(field_class, 'SQConfig') else False
            if special_insert:  # Special Insert with SQConfig.convert
                data_for_save[field_name] = field_class.SQConfig.convert(field_value)

            elif field.type_ in SPECIALTYPE or typing.get_origin(field.type_):  
                # typing._SpecialForm: Any, NoReturn, ClassVar, Union, Optional
                # typing.get_origin(field.type_) -> e.g. Literal
                data_for_save[field_name] = self._typing_conversion(field, field_value)

            elif issubclass(field.type_, BaseModel):  # nested BaseModels in this value
                # the value has got a field which is of type BaseModel, so this filed must be in a foreign table
                # if the field is already in the Table it continues, but if is it not in the table it will add this to the table
                # !recursive call to self.add

                if field_name not in foreign_tables.keys():
                    keys = list(foreign_tables.keys())
                    raise KeyError(f"detect field of Type BaseModel, but can not find '{field_name}' in foreign_tables (Keys: {keys})") from None
                else:
                    foreign_table_name = foreign_tables[field_name]

                if foreign_table_name not in self._db.table_names():
                    raise KeyError(f"Can not add a value, which has a foreign Key '{foreign_tables}' to a Table '{foreign_table_name}' which does not exists")

                nested_obj_ids = self._upsert_value_in_foreign_table(field_value, foreign_table_name, update_nested_models)
                data_for_save[field_name] = nested_obj_ids
                foreign_keys.append((field_name, foreign_table_name, pk))  # ignore=True

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

    def value_from_table(self, tablename: str, uuid: str) -> typing.Any:
        """searchs the Objekt with the given uuid in the table and returns it. Returns a subclass of type pydantic.BaseModel"""
        hits = [row for row in self._db[tablename].rows_where("uuid = ?", [uuid])]
        if len(hits) > 1:
            raise Exception("uuid is two times in table")  # TODO choice correct exceptiontype
 
        model = self._basemodels[tablename]
        foreign_refs = {key.column: key.other_table for key in self._db[tablename].foreign_keys}
        return None if not hits else self._build_basemodel_from_dict(model, hits[0], foreign_refs=foreign_refs)

    def values_in_table(self, tablename) -> int:
        """returns the number of values in the Table"""
        return self._db[tablename].count

    def load(self, filename: str) -> None:
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

    def save(self, filename: str) -> None:
        """saves alle values from the in_memory database to a file"""
        if not filename.endswith(".db"):
            filename += ".db"

        tmp_dir = tempfile.mkdtemp()
        name = filename.split(os.path.sep)[-1]
        tmp_name = tmp_dir + os.path.sep + name
        backup = tmp_dir + os.path.sep + "_backup.db"

        if os.path.isfile(filename):
            copyfile(filename, backup)
        try:
            file_db = sqlite3.connect(tmp_name)
            query = "".join(line for line in self._db.conn.iterdump())
            file_db.executescript(query)
            file_db.close()
            copyfile(tmp_name, filename)
        except Exception:
            print(f"saved the backup file under '{backup}'")

    def _basemodels_add_model(self, **kwargs):
        model = TableBaseModel(**kwargs)
        self._basemodels.update({kwargs['table']: model})
        self._db["__basemodels__"].upsert(model.data(), pk="modulename")

    def _build_basemodel_from_dict(self, basemodel: TableBaseModel, row: dict, foreign_refs: dict):
        # returns a subclass object of type BaseModel which is build out of class basemodel.moduleclass and the data out of the dict

        members = inspect.getmembers(basemodel.moduleclass, lambda a: not(inspect.isroutine(a)))
        field_models = next(line[1] for line in members if '__fields__' in line)

        d = {}
        for field_name, field_value in row.items():
            type_repr = field_models[field_name].__str__().split(' ')[1]  # 'type=Any'

            if field_name in foreign_refs.keys():  # the column contains another subclass of BaseModel
                if not iterable_in_type_repr(type_repr):
                    data = self.value_from_table(foreign_refs[field_name], field_value)
                else:
                    data = [self.value_from_table(foreign_refs[field_name], val) for val in json.loads(field_value)]
            else:  
                data = field_value if not iterable_in_type_repr(type_repr) else json.loads(field_value)
            d.update({field_name: data})

        return basemodel.moduleclass(**d)

    def _upsert_value_in_foreign_table(self, field_value, foreign_table_name, update_nested_models) -> Union[str, List[str]]:
        # The nested BaseModel will be inserted or upserted to the foreign table if it is not contained there,
        # or the update_nested_models parameter is True. If the value is Iterable (e.g. List) all values in the 
        # List will be be inserted or upserted. The function returns the ids of the values

        # The foreign keys of this table are needed to add the nested basemodel object.
        foreign_refs = {key.column: key.other_table for key in self._db.table(foreign_table_name).foreign_keys}

        def add_nested_model(value):
            if not self.value_in_table(foreign_table_name, value) or update_nested_models:
                self.add(foreign_table_name, value, foreign_tables=foreign_refs)
            return value.uuid

        if not isinstance(field_value, List):
            return add_nested_model(field_value)
        else:
            return [add_nested_model(element) for element in field_value]

    def _typing_conversion(self, field: ModelField, field_value: typing) -> typing.Any:
        if field.type_ == typing.Any:
            return field_value
        elif is_union_type(field.type_):
            return str(field_value)
        elif is_literal_type(field.type_):
            return str(field_value)
        else:
            raise NotImplementedError(f"type {field.type_} is not supported yet")
