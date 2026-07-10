"""Three passing tests — the fixture's observable green count."""

from src.widget import add


def check_add_basic():
    assert add(2, 3) == 5


def check_add_zero():
    assert add(0, 0) == 0


def check_add_negative():
    assert add(-1, 1) == 0
