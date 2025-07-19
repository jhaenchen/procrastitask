import unittest
from datetime import datetime
from procrastitask.dynamics.base_dynamic import BaseDynamic
from procrastitask.dynamics.combined_dynamic import CombinedDynamic
from procrastitask.dynamics.static_offset_dynamic import StaticOffsetDynamic

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

class TestZeroOutStaticDynamics(unittest.TestCase):
    def test_zero_out_static_in_combined(self):
        s1 = StaticOffsetDynamic(5)
        s2 = StaticOffsetDynamic(-3)
        d = DummyDynamic(2)
        c = CombinedDynamic([s1, d, s2], ["(+)", "(-)"])
        # Before zeroing
        self.assertEqual(s1.offset, 5)
        self.assertEqual(s2.offset, -3)
        c.zero_out_static_dynamics()
        self.assertEqual(s1.offset, 0)
        self.assertEqual(s2.offset, 0)
        # DummyDynamic should be unchanged
        self.assertEqual(d.value, 2)

    def test_zero_out_static_on_static(self):
        s = StaticOffsetDynamic(10)
        s.zero_out_static_dynamics()
        self.assertEqual(s.offset, 0)

    def test_zero_out_static_on_nested_combined(self):
        s1 = StaticOffsetDynamic(7)
        s2 = StaticOffsetDynamic(8)
        inner = CombinedDynamic([s1, s2], ["(+)"])
        d = DummyDynamic(1)
        outer = CombinedDynamic([inner, d], ["(+)"])
        outer.zero_out_static_dynamics()
        self.assertEqual(s1.offset, 0)
        self.assertEqual(s2.offset, 0)

if __name__ == "__main__":
    unittest.main()
