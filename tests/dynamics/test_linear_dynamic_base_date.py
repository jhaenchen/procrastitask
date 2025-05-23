from datetime import datetime, timedelta
import unittest
from procrastitask.task import Task, CompletionRecord
from procrastitask.dynamics.linear_dynamic import LinearDynamic
from freezegun import freeze_time

class TestTaskDynamicBaseDate(unittest.TestCase):
    def test_linear_dynamic_uses_cool_down_expiry(self):
        # Set up so that base_date is 1 hour in the past relative to now
        right_now = datetime(2025, 5, 22, 13, 0)
        last_completion = right_now - timedelta(hours=3)
        cooldown = timedelta(hours=1)
        cooldown_expiry = last_completion + cooldown  # 2 hours before right_now
        task = Task(
            title="CoolDownTask",
            description="desc",
            difficulty=1,
            duration=10,
            stress=5,
            cool_down="1hr",
            creation_date=right_now - timedelta(hours=4),
            last_refreshed=right_now - timedelta(hours=4),
            stress_dynamic=LinearDynamic(1),
        )
        task.history = [CompletionRecord(completed_at=last_completion, stress_at_completion=5)]
        with freeze_time(right_now):
            base_date = task.get_dynamic_base_date()
            self.assertEqual(base_date, cooldown_expiry)
            stress = task.get_rendered_stress()
            self.assertGreater(stress, 5)

    def test_linear_dynamic_uses_periodicity_boundary(self):
        # Set up so that the cron boundary is 4 hours in the past
        right_now = datetime(2025, 5, 22, 12, 0)
        cron = "0 8 * * *"
        # Last completion was 2 days ago, cron boundary is today at 8am (4 hours before now)
        last_completion = right_now - timedelta(days=2)
        cron_boundary = datetime(2025, 5, 22, 8, 0)
        task = Task(
            title="PeriodicTask",
            description="desc",
            difficulty=1,
            duration=10,
            stress=5,
            periodicity=cron,
            creation_date=right_now - timedelta(days=5),
            last_refreshed=right_now - timedelta(days=5),
            stress_dynamic=LinearDynamic(1),
        )
        task.history = [CompletionRecord(completed_at=last_completion, stress_at_completion=5)]
        with freeze_time(right_now):
            base_date = task.get_dynamic_base_date()
            self.assertEqual(base_date, cron_boundary)
            stress = task.get_rendered_stress()
            self.assertGreater(stress, 5)
