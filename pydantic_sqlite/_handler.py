import os
from contextlib import contextmanager

from ._core import DataBase
from ._misc import uniquify


class DB_Handler:

    def __init__(self, dbname: str = None):
        self._ctx = None
        if dbname and not dbname.endswith(".db"):
            dbname += ".db"
        self.dbname = dbname

    def __enter__(self):
        if self._ctx is not None:
            raise RuntimeError('DB_Handler is not reentrant')
        self._ctx = self._contextmanager()
        return self._ctx.__enter__()

    def __exit__(self, exc_type, exc, tb):
        assert self._ctx is not None, "Context was not entered"
        if exc_type:
            self.db.save(filename=uniquify(f"{self.dbname[:-3]}_crash.db"))
        return self._ctx.__exit__(exc_type, exc, tb)

    @contextmanager
    def _contextmanager(self):
        try:
            self.db = DataBase()
            if self.dbname and os.path.isfile(self.dbname):
                self.db.load(self.dbname)
            yield self.db
        finally:
            pass
