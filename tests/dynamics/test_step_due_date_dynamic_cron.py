import unittest
from datetime import datetime, timedelta
from procrastitask.dynamics.step_due_date_dynamic import StepDueDateDynamic
from procrastitask.task import Task
from freezegun import freeze_time

class TestStepDueDateDynamicWithCron(unittest.TestCase):
    def test_step_due_date_dynamic_with_cron(self):
        # Set up a task with a daily cron due date
        base = datetime(2025, 5, 20, 8, 0)
        cron = "0 8 * * 1"  # every Monday at 8am
        # Dynamic: +50% stress if within 2 days of due date
        dynamic = StepDueDateDynamic(increase_by_percentage=50, increase_days_before=2)
        # No completions, so current_due_date is next Monday after base
        task = Task(
            title="Test",
            description="desc",
            difficulty=1,
            duration=60,
            stress=10,
            due_date_cron=cron,
            creation_date=base,
            stress_dynamic=dynamic,
        )
        # Freeze time to 3 days before due date: should NOT get bonus
        # Due date is 2025-05-26 08:00 (next Monday)
        test_time = datetime(2025, 5, 23, 8, 0)  # Friday before due date
        with freeze_time(test_time):
            stress = dynamic.apply(test_time, 10, task)
            self.assertEqual(stress, 10)
        # Freeze time to 2 days before due date: should get bonus
        test_time = base + timedelta(days=8)
        with freeze_time(test_time):
            stress = dynamic.apply(test_time, 10, task)
            self.assertEqual(stress, 15)

if __name__ == "__main__":
    unittest.main()
