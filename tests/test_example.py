

from procrastitask.task import Task


def test_example():
    assert 1 + 1 == 2

def import_works():
    assert Task.is_complete is not None