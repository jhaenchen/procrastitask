import unittest
from datetime import datetime, timedelta
from procrastitask.dynamics.step_due_date_dynamic import StepDueDateDynamic
from procrastitask.dynamics.base_dynamic import BaseDynamic
from procrastitask.task import Task

class TestStepDueDateDynamic(unittest.TestCase):

    def setUp(self):
        self.base_stress = 100
        self.increase_by_percentage = 2
        self.increase_days_before = 5
        self.dynamic = StepDueDateDynamic(
            increase_by_percentage=self.increase_by_percentage,
            increase_days_before=self.increase_days_before
        )
        self.base_task = Task(title="Test Task", description="Test Description", difficulty=1, duration=1, stress=self.base_stress)

    def test_apply_with_due_date(self):
        due_date = datetime.now() + timedelta(days=3)
        self.base_task.due_date = due_date
        task = self.base_task
        new_stress = self.dynamic.apply(datetime.now(), self.base_stress, task)
        expected_stress = self.base_stress * (1 + (self.increase_by_percentage / 100))
        self.assertEqual(new_stress, expected_stress)

    def test_apply_without_due_date(self):
        task = self.base_task
        task.due_date = None
        with self.assertRaises(ValueError):
            self.dynamic.apply(datetime.now(), self.base_stress, task)

    def test_apply_with_due_date_after_threshold(self):
        due_date = datetime.now() + timedelta(days=10)
        self.base_task.due_date = due_date
        task = self.base_task
        new_stress = self.dynamic.apply(datetime.now(), self.base_stress, task)
        self.assertEqual(new_stress, self.base_stress)

    def test_from_text(self):
        text = "dynamic-step-due.5.2"
        dynamic = StepDueDateDynamic.from_text(text)
        self.assertEqual(dynamic.increase_days_before, 5)
        self.assertEqual(dynamic.increase_by_percentage, 2)

    def test_to_text(self):
        text = self.dynamic.to_text()
        expected_text = f"dynamic-step-due.{self.increase_days_before}.{self.increase_by_percentage}"
        self.assertEqual(text, expected_text)

if __name__ == "__main__":
    unittest.main()