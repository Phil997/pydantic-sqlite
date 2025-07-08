import os
from pathlib import Path

from pydantic_sqlite._misc import get_unique_filename


def test_uniquify(tmp_path: Path):
    testfile = tmp_path / "file.txt"

    for _ in range(3):
        name = get_unique_filename(testfile)
        tmp_path.joinpath(name).touch()

    assert set(os.listdir(tmp_path)) == set(('file.txt', 'file(1).txt', 'file(2).txt'))
