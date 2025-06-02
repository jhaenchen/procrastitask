import unittest
from datetime import datetime, timedelta

from procrastitask.dynamics.base_dynamic import BaseDynamic
from procrastitask.dynamics.combined_dynamic import CombinedDynamic
from procrastitask.dynamics.linear_dynamic import LinearDynamic
from procrastitask.dynamics.static_offset_dynamic import StaticOffsetDynamic
from procrastitask.task import Task
from freezegun import freeze_time

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

class TestCombinedDynamic(unittest.TestCase):
    def test_combined_dynamic_pipe_plus(self):
        d0 = DummyDynamic(0)
        d1 = DummyDynamic(5)
        d2 = DummyDynamic(10)
        c = CombinedDynamic([d0, d1, d2], ["(|+)", "(+)"])
        result = c.apply(datetime.now(), 100, None)
        self.assertEqual(result, 100)  # d0 yields 0, so (|+) skips d1 and d2

        d0 = DummyDynamic(1)
        c = CombinedDynamic([d0, d1, d2], ["(|+)", "(+)"])
        result = c.apply(datetime.now(), 100, None)
        expected = 100 + d0.value + d1.value + d2.value
        self.assertEqual(result, expected)

        d0 = DummyDynamic(-2)
        c = CombinedDynamic([d0, d1], ["(|+)"])
        result = c.apply(datetime.now(), 100, None)
        expected = 100 + d0.value + d1.value
        self.assertEqual(result, expected)

        d0 = DummyDynamic(1)
        d1 = DummyDynamic(0)
        d2 = DummyDynamic(10)
        c = CombinedDynamic([d0, d1, d2], ["(+)", "(|+)"])
        result = c.apply(datetime.now(), 100, None)
        expected = 100 + d0.value + d1.value
        self.assertEqual(result, expected)

    def test_combined_dynamic_static_offset(self):
        right_now = datetime.now()
        base_stress = 10
        static_offset_dynamic = StaticOffsetDynamic(offset=1)
        other_static_offset_dynamic = StaticOffsetDynamic(offset=2)
        combined_dynamic = BaseDynamic.find_dynamic(f"{static_offset_dynamic.to_text()} (+) {other_static_offset_dynamic.to_text()}")
        self.assertIsInstance(combined_dynamic, CombinedDynamic)
        created_task = Task(
            "Test task",
            "description",
            10,
            10,
            stress=base_stress,
            periodicity=None,
            stress_dynamic=combined_dynamic,
            creation_date=right_now,
            last_refreshed=right_now,
            due_date=right_now + timedelta(days=5)
        )
        with freeze_time(right_now + timedelta(days=1)):
            rendered_stress = created_task.get_rendered_stress()
            expected_stress = base_stress + 3
            self.assertEqual(rendered_stress, expected_stress)

    def test_combined_dynamic_addition(self):
        right_now = datetime.now()
        base_stress = 10
        linear_dynamic = LinearDynamic(1)
        combined_dynamic = BaseDynamic.find_dynamic(f"{linear_dynamic.to_text()} (+) {linear_dynamic.to_text()}")
        self.assertIsInstance(combined_dynamic, CombinedDynamic)
        created_task = Task(
            "Test task",
            "description",
            10,
            10,
            stress=base_stress,
            periodicity=None,
            stress_dynamic=combined_dynamic,
            creation_date=right_now,
            last_refreshed=right_now,
            due_date=right_now + timedelta(days=5)
        )
        with freeze_time(right_now + timedelta(days=1)):
            rendered_stress = created_task.get_rendered_stress()
            expected_stress = base_stress + 2
            self.assertEqual(rendered_stress, expected_stress)

    def test_combined_dynamic_subtraction(self):
        right_now = datetime.now()
        base_stress = 10
        linear_dynamic = LinearDynamic(1)
        combined_dynamic = BaseDynamic.find_dynamic(f"{linear_dynamic.to_text()} (-) {LinearDynamic(2).to_text()}")
        self.assertIsInstance(combined_dynamic, CombinedDynamic)
        created_task = Task(
            "Test task",
            "description",
            10,
            10,
            stress=base_stress,
            periodicity=None,
            stress_dynamic=combined_dynamic,
            creation_date=right_now,
            last_refreshed=right_now,
            due_date=right_now + timedelta(days=5)
        )
        with freeze_time(right_now + timedelta(days=1)):
            rendered_stress = created_task.get_rendered_stress()
            expected_stress = base_stress + .5  # 1 - 0.5 = 0.5
            self.assertEqual(rendered_stress, expected_stress)

if __name__ == "__main__":
    unittest.main()
