import os
from contextlib import contextmanager
from typing import Any, Generator, Optional

from ._core import DataBase
from ._misc import get_unique_filename


class DB_Handler:
    dbname: Optional[str]
    db: DataBase
    _ctx: Optional[Any]

    def __init__(self, dbname: Optional[str] = None) -> None:
        self._ctx: Optional[Any] = None
        if dbname and not dbname.endswith(".db"):
            dbname += ".db"
        self.dbname: Optional[str] = dbname

    def __enter__(self) -> DataBase:
        if self._ctx is not None:
            raise RuntimeError('DB_Handler is not reentrant')
        self._ctx = self._contextmanager()
        return self._ctx.__enter__()

    def __exit__(self, exc_type: Optional[type], exc: Optional[BaseException], tb: Optional[Any]) -> Optional[bool]:
        assert self._ctx is not None, "Context was not entered"
        if exc_type:
            self.db.save(filename=get_unique_filename(f"{self.dbname[:-3]}_crash.db"))
        return self._ctx.__exit__(exc_type, exc, tb)

    @contextmanager
    def _contextmanager(self) -> Generator[DataBase, None, None]:
        try:
            self.db = DataBase()
            if self.dbname and os.path.isfile(self.dbname):
                self.db.load(self.dbname)
            yield self.db
        finally:
            pass
