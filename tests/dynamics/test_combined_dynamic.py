import pytest
from datetime import datetime, timedelta
from procrastitask.dynamics.base_dynamic import CombinedDynamic, BaseDynamic

class DummyDynamic(BaseDynamic):
    prefixes = ["dummy"]
    def __init__(self, value):
        self.value = value
    @staticmethod
    def from_text(text):
        return DummyDynamic(int(text.replace("dummy", "")))
    def to_text(self):
        return f"dummy{self.value}"
    def apply(self, creation_date, base_stress, task):
        return base_stress + self.value

def test_combined_dynamic_pipe_plus():
    # Setup: first dynamic yields 0, second yields 5, third yields 10
    d0 = DummyDynamic(0)
    d1 = DummyDynamic(5)
    d2 = DummyDynamic(10)
    # Only d1 and d2 should be summed if d0 is nonzero, but d0 is zero, so only d0 applies
    c = CombinedDynamic([d0, d1, d2], ["(|+)", "(+)"])
    result = c.apply(datetime.now(), 100, None)
    assert result == 100  # d0 yields 0, so (|+) skips d1 and d2

    # Now, d0 yields 1, so d1 is added, then d2 is added
    d0 = DummyDynamic(1)
    c = CombinedDynamic([d0, d1, d2], ["(|+)", "(+)"])
    result = c.apply(datetime.now(), 100, None)
    expected = 100 + d0.value + d1.value + d2.value
    assert result == expected

    # Test with negative diff
    d0 = DummyDynamic(-2)
    c = CombinedDynamic([d0, d1], ["(|+)"])
    result = c.apply(datetime.now(), 100, None)
    expected = 100 + d0.value + d1.value
    assert result == expected

    # Test with (|+) after a zero diff in the middle
    d0 = DummyDynamic(1)
    d1 = DummyDynamic(0)
    d2 = DummyDynamic(10)
    c = CombinedDynamic([d0, d1, d2], ["(+)", "(|+)"])
    result = c.apply(datetime.now(), 100, None)
    # d0=1, d1=0, (|+) skips d2
    expected = 100 + d0.value + d1.value
    assert result == expected
