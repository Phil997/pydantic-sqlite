import os

import pytest
from testfixtures import TempDirectory

from pydantic_sqlite._misc import get_unique_filename


@pytest.fixture()
def dir():
    with TempDirectory() as dir:
        yield dir


def test_uniquify(dir):
    testfile = dir.path + os.path.sep + "foo.txt"
    examples = 10

    for _ in range(examples):
        dir.write(get_unique_filename(testfile), b'some foo thing')

    assert len(set(os.listdir(dir.path))) == examples
