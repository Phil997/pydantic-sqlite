import os

import pytest
from pydantic_sqlite._misc import uniquify
from testfixtures import TempDirectory


@pytest.fixture()
def dir():
    with TempDirectory() as dir:
        yield dir

def test_uniquify(dir):
    testfile = dir.path + os.path.sep + "foo.txt"
    examples = 10

    for _ in range(examples):
        dir.write(uniquify(testfile), b'some foo thing')

    assert len(set(os.listdir(dir.path))) == examples
