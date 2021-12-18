import os

import pytest
from pydantic_sqlite._misc import remove_file, uniquify
from testfixtures import TempDirectory


@pytest.fixture()
def dir():
    with TempDirectory() as dir:
        yield dir

def test_remove_file(dir):
    testfile = "test.txt"
    dir.write(testfile, b'some foo thing')

    assert testfile in os.listdir(dir.path)
    remove_file(f"{dir.path}\\{testfile}")
    assert testfile not in os.listdir(dir.path)


def test_uniquify(dir):
    testfile = f"{dir.path}\\foo.txt"
    examples = 10

    for _ in range(examples):
        dir.write(uniquify(testfile), b'some foo thing')

    assert len(set(os.listdir(dir.path))) == examples
