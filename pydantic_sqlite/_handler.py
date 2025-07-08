import os
from contextlib import _GeneratorContextManager, contextmanager
from typing import Any, Generator, Optional

from ._core import DataBase
from ._misc import get_unique_filename


class DB_Handler:
    """
    A context manager wrapper for the DataBase class that provides automatic db snapshotting on an exception.

    When used as a context manager, DB_Handler returns a DataBase instance. If an exception occurs
    within the context, it saves a snapshot of the database to a file named '<dbname>_snapshot.db' by default.
    If such a file already exists, the filename is incremented (e.g., '<dbname>_snapshot(1).db').
    The snapshot suffix can be configured via the constructor.
    """
    dbname: str
    db: DataBase
    _ctx: Optional[_GeneratorContextManager]
    snapshot_suffix: str

    def __init__(self, dbname: str, snapshot_suffix: str = "_snapshot.db") -> None:
        """
        Initialize the DB_Handler with the given database name and snapshot suffix.
        Ensures the database filename ends with '.db'.

        Args:
            dbname (str): The name of the database file (with or without '.db' extension).
            snapshot_suffix (str): The suffix to use for snapshot files (default: '_snapshot.db').
        """
        self._ctx = None
        if not dbname.endswith(".db"):
            dbname += ".db"
        self.dbname = dbname
        self.snapshot_suffix = snapshot_suffix

    def __enter__(self) -> DataBase:
        """
        Enters the context manager, returning a DataBase instance.
        Raises an error if the handler is re-entered.

        Returns:
            DataBase: The database instance for use within the context.
        """
        if self._ctx is not None:
            raise RuntimeError('DB_Handler is not reentrant')
        self._ctx = self._contextmanager()
        return self._ctx.__enter__()

    def __exit__(self, exc_type: Optional[type], exc: Optional[BaseException], tb: Optional[Any]) -> Optional[bool]:
        """
        Exits the context manager. If an exception occurred, saves a snapshot of the database.

        Args:
            exc_type (Optional[type]): The exception type, if any.
            exc (Optional[BaseException]): The exception instance, if any.
            tb (Optional[Any]): The traceback, if any.

        Returns:
            Optional[bool]: The result of the context manager's __exit__ method.
        """
        assert self._ctx is not None, "Context was not entered"
        if exc_type:
            self.db.save(filename=get_unique_filename(f"{self.dbname[:-3]}{self.snapshot_suffix}"))
        return self._ctx.__exit__(exc_type, exc, tb)

    @contextmanager
    def _contextmanager(self) -> Generator[DataBase, None, None]:
        """
        Internal context manager that creates or loads the database.
        Loads the database from file if it exists, otherwise creates a new one.

        Yields:
            DataBase: The database instance for use within the context.
        """
        try:
            self.db = DataBase()
            if os.path.isfile(self.dbname):
                self.db.load(self.dbname)
            yield self.db
        finally:
            pass
