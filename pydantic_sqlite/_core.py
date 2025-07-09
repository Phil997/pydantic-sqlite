import importlib
import inspect
import json
import logging
import os
import sqlite3
import tempfile
import typing
from pathlib import Path
from shutil import copyfile
from typing import Any, Dict, Generator, List, Literal, Union, get_origin

from pydantic import BaseModel
from pydantic._internal._model_construction import ModelMetaclass
from pydantic.fields import FieldInfo
from sqlite_utils import Database as _Database

from ._misc import convert_value_into_union_types

SPECIALTYPE = [Any, Literal, Union]


class TableBaseModel:
    """
    Stores metadata about a table and its associated Pydantic BaseModel class.

    Attributes:
        table (str): The name of the table.
        basemodel_cls (ModelMetaclass): The Pydantic BaseModel class for the table.
        modulename (str): The module name of the BaseModel class.
        pks (List[str]): List of primary key field names.
    """

    table: str
    basemodel_cls: ModelMetaclass
    modulename: str
    pks: List[str]

    def __init__(
        self, table: str, basemodel_cls: ModelMetaclass, pks: List[str]
    ) -> None:
        """
        Initialize TableBaseModel with table name, BaseModel class, and primary keys.

        Args:
            table (str): The name of the table.
            basemodel_cls (ModelMetaclass): The Pydantic BaseModel class for the table.
            pks (List[str]): List of primary key field names.
        """
        self.table = table
        self.basemodel_cls = basemodel_cls
        self.modulename = str(basemodel_cls).split("<class '")[1].split("'>")[0]
        self.pks = pks

    def data(self) -> Dict[str, Union[str, List[str]]]:
        """
        Return a dictionary representation of the table metadata.
        """
        return dict(table=self.table, modulename=self.modulename, pks=self.pks)


class DataBase:
    """
    Main interface for storing and retrieving Pydantic BaseModels in an SQLite database.
    Provides methods for adding, querying, saving, and loading models,
    as well as handling foreign keys and nested models.
    """

    _basemodels: Dict[str, TableBaseModel]
    _db: _Database

    def __init__(
        self,
        filename_or_conn: Union[str, Path, sqlite3.Connection, None] = None,
        **kwargs,
    ) -> None:
        """
        Initialize the DataBase. If no filename or connection is provided, creates an in-memory database.

        Args:
            filename_or_conn (Union[str, Path, sqlite3.Connection, None], optional):
                The filename, Path, or sqlite3.Connection to use for the database. If None, uses in-memory DB.
            **kwargs: Additional keyword arguments passed to sqlite_utils.Database.
        """
        self._basemodels = {}
        if filename_or_conn is None:
            self._db = _Database(memory=True, **kwargs)
        else:
            self._db = _Database(filename_or_conn, **kwargs)

    def __call__(self, tablename: str, **kwargs) -> Generator[BaseModel, None, None]:
        """
        Returns a generator for all values in the table as subclasses of `pydantic.BaseModel`.

        Args:
            tablename (str): Name of the table.
            kwargs: Additional arguments passed to `rows_where` (e.g., where, where_args, order_by, limit, offset).

        Yields:
            BaseModel: Instances from the table.
        """
        try:
            basemodel = self._basemodels[tablename]
            foreign_refs = {key.column: key.other_table for key in self._db[tablename].foreign_keys}
        except KeyError:
            raise KeyError(f"Can't find table '{tablename}' in Database") from None

        for row in self._db[tablename].rows_where(**kwargs):
            yield self._build_basemodel_from_dict(basemodel, row, foreign_refs)

    @property
    def filename(self) -> str:
        """
        Returns the filename of the database. If in-memory, returns ':memory:'.
        """
        db_filename = self._db.conn.execute("PRAGMA database_list").fetchone()[2]
        if db_filename in {"", ":memory:"}:
            return ":memory:"
        else:
            return db_filename

    def add(  # noqa: C901
        self,
        tablename: str,
        value: BaseModel,
        foreign_tables: dict = dict(),
        update_nested_models: bool = True,
        pk: str = "uuid",
    ) -> None:
        """
        Adds a new value to the specified table. Handles nested models and foreign keys.

        Args:
            tablename (str): The name of the table.
            value (BaseModel): The value to be added, as a Pydantic BaseModel instance.
            foreign_tables (dict, optional): A dictionary of foreign tables and their mappings.
            update_nested_models (bool, optional): Whether to update nested models if they already exist.
            pk (str, optional): The primary key field name. Defaults to "uuid".
        """
        # unkown Tablename -> means new Table -> update the table_basemodel_ref list
        if not isinstance(value, BaseModel):
            raise TypeError("Only pydantic BaseModels can be added to the database")

        if tablename not in self._basemodels:
            self._basemodels_add_model(table=tablename, basemodel_cls=type(value), pks=[pk])

        if not isinstance(value, self._basemodels[tablename].basemodel_cls):
            _table_type = self._basemodels[tablename].basemodel_cls.__name__
            msg = f"Only pydantic BaseModels of type '{_table_type}' can be added to the table '{tablename}'"
            raise TypeError(msg)

        # create dict for writing to the Table
        data_for_save = (
            value.model_dump()
            if not hasattr(value, "sqlite_repr")
            else value.sqlite_repr
        )

        foreign_keys = []
        for field_name, field_info in value.model_fields.items():
            field_value = getattr(value, field_name)

            if res := self._special_conversion(field_value):  # Special Insert with SQConfig.convert
                data_for_save[field_name] = res

            elif field_info.annotation == Any or get_origin(field_info.annotation) is Union:
                data_for_save[field_name] = field_value

            elif get_origin(field_info.annotation) is Literal:
                data_for_save[field_name] = str(field_value)

            elif get_origin(field_info.annotation) is list:
                obj = typing.get_args(field_info.annotation)[0]
                if inspect.isclass(obj) and issubclass(obj, BaseModel):
                    data_for_save[field_name] = [x.uuid for x in field_value]
                    foreign_table_name = self._get_foreign_table_name(field_name, foreign_tables)
                    foreign_keys.append((field_name, foreign_table_name, pk))
                else:
                    data_for_save[field_name] = [str(x) for x in field_value]

            elif inspect.isclass(field_info.annotation) and issubclass(field_info.annotation, BaseModel):
                # the value has got a field which is of type BaseModel, so this filed must be in a foreign table
                # if the field is already in the Table it continues, but if is it not in the table it will add this
                # to the table recursive call to self.add
                foreign_table_name = self._get_foreign_table_name(field_name, foreign_tables)
                nested_obj_ids = self._upsert_value_in_foreign_table(
                    field_value,
                    foreign_table_name,
                    update_nested_models)
                data_for_save[field_name] = nested_obj_ids
                foreign_keys.append((field_name, foreign_table_name, pk))  # ignore=True

        self._db[tablename].upsert(data_for_save, pk=pk, foreign_keys=foreign_keys)

    def _get_foreign_table_name(self, field_name: str, foreign_tables: dict) -> str:
        """
        Searches in the dict 'foreign_tables' for the field_name and returns the matching tablename.
        If it is not found, raises KeyError.

        Args:
            field_name (str): The name of the field.
            foreign_tables (dict): A dictionary of foreign tables and their mappings.

        Returns:
            str: The name of the foreign table.
        """
        if field_name not in foreign_tables.keys():
            keys = list(foreign_tables.keys())
            msg = f"detect field of Type BaseModel, but can not find '{field_name}'"
            msg += f"in foreign_tables (Keys: {keys})"
            raise KeyError(msg) from None
        else:
            foreign_table_name = foreign_tables[field_name]

        if foreign_table_name not in self._db.table_names():
            msg = f"Can not add a value, which has a foreign Key '{foreign_tables}'"
            msg += f" to a Table '{foreign_table_name}' which does not exists"
            raise KeyError(msg)
        return foreign_table_name

    def value_in_table(self, tablename: str, pk_value: Union[str, BaseModel], pk: str = "uuid") -> bool:
        """
        Checks if the given value is in the table.
        The value can either be an instance of the BaseModel or the primary_key value itself.
        If it is a BaseModel instance, the primary key will be extracted using `getattr` with the specified `pk`.

        Args:
            tablename (str): Name of the table to search in.
            pk_value (str | BaseModel): The value of the primary key to look for,
              or a BaseModel instance (the key will be extracted with getattr with pk).
            pk (str, optional): The primary key field name. Defaults to "uuid".

        Returns:
            bool: True if a row with the given primary key exists, otherwise False.
        """
        if isinstance(pk_value, BaseModel):
            pk_value = getattr(pk_value, pk)
        entries = [row for row in self._db[tablename].rows_where(f"{pk} = ?", [pk_value])]
        return bool(entries)

    def value_from_table(self, tablename: str, pk_value: str, pk: str = "uuid") -> typing.Any:
        """
        Retrieve a BaseModel instance from the table by primary key.

        Args:
            tablename (str): Name of the table to search in.
            pk_value (str): The value of the primary key to look for.
            pk (str, optional): The primary key field name. Defaults to "uuid".

        Returns:
            BaseModel | None: The found object as a BaseModel subclass, or None if not found.
        """
        entries = [row for row in self._db[tablename].rows_where(f"{pk} = ?", [pk_value])]

        model = self._basemodels[tablename]
        foreign_refs = {key.column: key.other_table for key in self._db[tablename].foreign_keys}

        if not entries:
            return None
        else:
            return self._build_basemodel_from_dict(model, entries[0], foreign_refs=foreign_refs)

    def values_in_table(self, tablename: str) -> int:
        """
        Returns the number of values in the table.

        Args:
            tablename (str): The name of the table.

        Returns:
            int: The number of values in the table.
        """
        return self._db[tablename].count

    def load(self, filename: str) -> None:
        """
        Loads all data from the given file and adds them to the in-memory database.
        Raises FileNotFoundError if the file does not exist.

        Args:
            filename (str): The path to the file to load.
        """
        if not os.path.isfile(filename):
            raise FileNotFoundError(f"Can not load {filename}")
        file_db = sqlite3.connect(filename)
        query = "".join(line for line in file_db.iterdump())
        self._db.conn.executescript(query)
        file_db.close()

        for model in self._db["__basemodels__"].rows:
            classname = model["modulename"].split(".")[-1]
            modulename = ".".join(model["modulename"].split(".")[:-1])
            my_module = importlib.import_module(modulename)
            self._basemodels_add_model(
                table=model["table"],
                basemodel_cls=getattr(my_module, classname),
                pks=json.loads(model["pks"]),
            )

    def save(self, filename: str) -> None:
        """
        Saves all values from the in-memory database to a file.
        If the database is persistent, does nothing and returns None.

        Args:
            filename (str): The path to the file where the database should be saved.
        """
        if self.filename != ":memory:":
            logging.warning(f"database is persistent, already stored in a file: {self.filename}")
            return

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
            logging.warning(f"saved the backup file under '{backup}'")
            raise

    def _basemodels_add_model(self, **kwargs) -> None:
        """
        Adds a TableBaseModel to the internal registry and upserts its metadata.

        Args:
            **kwargs: TableBaseModel attributes (table, basemodel_cls, pks).
        """
        model = TableBaseModel(**kwargs)
        self._basemodels.update({kwargs["table"]: model})
        self._db["__basemodels__"].upsert(model.data(), pk="modulename")

    def _build_basemodel_from_dict(
        self, tablemodel: TableBaseModel, row: dict, foreign_refs: dict
    ) -> BaseModel:
        """
        Builds a BaseModel instance from a row dictionary, handling nested and foreign key fields.

        Args:
            tablemodel (TableBaseModel): The TableBaseModel instance for the table.
            row (dict): The row data as a dictionary.
            foreign_refs (dict): A dictionary of foreign key references.

        Returns:
            BaseModel: The constructed BaseModel instance.
        """
        # returns a subclass object of type BaseModel which is build out of
        # class basemodel.basemodel_cls and the data out of the dict
        field_models: Dict[str, FieldInfo] = tablemodel.basemodel_cls.model_fields
        tablemodel.basemodel_cls
        d = {}

        for field_name, field_value in row.items():
            info = field_models[field_name]

            if (field_name in foreign_refs.keys()):  # the column contains another subclass of BaseModel
                if get_origin(info.annotation) == list:
                    data = [
                        self.value_from_table(foreign_refs[field_name], val)
                        for val in json.loads(field_value)
                    ]
                else:
                    data = self.value_from_table(foreign_refs[field_name], field_value)
            else:
                if get_origin(info.annotation) == list:
                    data = json.loads(field_value)
                elif get_origin(info.annotation) == Union:
                    data = convert_value_into_union_types(info.annotation, field_value)
                else:
                    data = field_value

            d.update({field_name: data})
        return tablemodel.basemodel_cls(**d)

    def _upsert_value_in_foreign_table(
        self, field_value: typing.Any, foreign_table_name: str, update_nested_models: bool
    ) -> Union[str, List[str]]:
        """
        Inserts or upserts a nested BaseModel or list of BaseModels into a foreign table.
        Returns the uuid(s) of the inserted/updated values.

        Args:
            field_value (typing.Any): The nested BaseModel or list of BaseModels to insert or upsert.
            foreign_table_name (str): The name of the foreign table.
            update_nested_models (bool): Whether to update nested models if they already exist.

        Returns:
            Union[str, List[str]]: The uuid or list of uuids of the inserted/updated values.
        """
        # The nested BaseModel will be inserted or upserted to the foreign table if it is not contained there,
        # or the update_nested_models parameter is True. If the value is Iterable (e.g. List) all values in the
        # List will be be inserted or upserted. The function returns the ids of the values

        # The foreign keys of this table are needed to add the nested basemodel object.
        foreign_refs = {
            key.column: key.other_table
            for key in self._db.table(foreign_table_name).foreign_keys
        }

        def add_nested_model(value):
            if (
                not self.value_in_table(foreign_table_name, value.uuid)
                or update_nested_models
            ):
                self.add(foreign_table_name, value, foreign_tables=foreign_refs)
            return value.uuid

        if not isinstance(field_value, List):
            return add_nested_model(field_value)
        else:
            return [add_nested_model(element) for element in field_value]

    def _special_conversion(self, field_value: Any) -> Union[bool, Any]:
        """
        Handles special conversion for fields with SQConfig and custom convert methods.
        Returns the converted value or False if not applicable.

        Args:
            field_value (Any): The field value to convert.

        Returns:
            Union[bool, Any]: The converted value or False.
        """
        def special_possible(obj_class):
            try:
                if not hasattr(obj_class.SQConfig, "convert"):
                    return False
                return True if obj_class.SQConfig.special_insert else False
            except AttributeError:
                return False

        if isinstance(field_value, List):
            if len(field_value) == 0:
                return False

            if not special_possible(obj_class := field_value[0].__class__):
                return False
            if not all(isinstance(value, type(field_value[0])) for value in field_value):
                raise ValueError(f"not all values in the List are from the same type: '{field_value}'")
            return [obj_class.SQConfig.convert(value) for value in field_value]
        else:
            if not special_possible(obj_class := field_value.__class__):
                return False
            return obj_class.SQConfig.convert(field_value)
