import os
from contextlib import _GeneratorContextManager, contextmanager
from typing import Any, Generator, Optional

from ._core import DataBase
from ._misc import get_unique_filename


class FailSafeDataBase:
    """
    Context manager for the DataBase class that automatically creates a database snapshot if
    an unexpected exception occurs.

    When used as a context manager, FailSafeDataBase returns a DataBase instance. If an exception occurs
    within the context, it saves a snapshot of the database to a file named '<dbname>_snapshot.db' by default.
    If such a file already exists, the filename is incremented (e.g., '<dbname>_snapshot(1).db').
    The snapshot suffix can be configured via the constructor.

    This class is designed to be fail-safe: if an error or exception interrupts database operations,
    a backup snapshot is automatically created to prevent data loss.

    Attributes:
        dbname (str): The name of the database file.
        db (DataBase): The database instance managed by this context manager.
        _ctx (Optional[_GeneratorContextManager]): Internal context manager state.
        snapshot_suffix (str): Suffix for snapshot files (default: '_snapshot.db').
    """
    dbname: str
    db: DataBase
    _ctx: Optional[_GeneratorContextManager]
    snapshot_suffix: str

    def __init__(self, dbname: str, snapshot_suffix: str = "_snapshot.db", **kwargs) -> None:
        """
        Initialize the FailSafeDataBase with the given database name and snapshot suffix.
        Ensures the database filename ends with '.db'.

        Args:
            dbname (str): The name of the database file (with or without '.db' extension).
            snapshot_suffix (str): The suffix to use for snapshot files (default: '_snapshot.db').
            **kwargs: Additional keyword arguments to pass to the DataBase constructor.
        """
        self._ctx = None
        if not dbname.endswith(".db"):
            dbname += ".db"
        self.dbname = dbname
        self.snapshot_suffix = snapshot_suffix
        self._db_kwargs = kwargs

    def __enter__(self) -> DataBase:
        """
        Enter the context manager, returning a DataBase instance.
        Raises an error if the manager is re-entered.

        Returns:
            DataBase: The database instance for use within the context.
        """
        if self._ctx is not None:
            raise RuntimeError('FailSafeDataBase is not reentrant')
        self._ctx = self._contextmanager()
        return self._ctx.__enter__()

    def __exit__(self, exc_type: Optional[type], exc: Optional[BaseException], tb: Optional[Any]) -> Optional[bool]:
        """
        Exit the context manager. If an exception occurred, automatically saves a snapshot of the database.

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
            self.db = DataBase(**self._db_kwargs)
            if os.path.isfile(self.dbname):
                self.db.load(self.dbname)
            yield self.db
        finally:
            pass
