from datetime import datetime, timedelta
import unittest
from procrastitask.task import Task, CompletionRecord
from procrastitask.dynamics.linear_dynamic import LinearDynamic
from freezegun import freeze_time

class TestTaskDynamicBaseDate(unittest.TestCase):
    def test_linear_dynamic_uses_cool_down_expiry(self):
        right_now = datetime(2025, 5, 22, 12, 0)
        # Cool down is 1 hour, last completion was 3 hours ago
        # So cooldown expired 2 hours ago
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
        task.history = [CompletionRecord(completed_at=right_now - timedelta(hours=3), stress_at_completion=5)]
        with freeze_time(right_now):
            base_date = task.get_dynamic_base_date()
            self.assertEqual(base_date, task.history[-1].completed_at + timedelta(hours=1))
            # LinearDynamic should use this base date
            stress = task.get_rendered_stress()
            self.assertGreater(stress, 5)

    def test_linear_dynamic_uses_periodicity_boundary(self):
        right_now = datetime(2025, 5, 22, 12, 0)
        # Periodicity: every day at 8am, last completion was 2 days ago
        cron = "0 8 * * *"
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
        task.history = [CompletionRecord(completed_at=right_now - timedelta(days=2), stress_at_completion=5)]
        with freeze_time(right_now):
            base_date = task.get_dynamic_base_date()
            # Should be the most recent cron boundary before now
            from croniter import croniter
            prev_period = croniter(cron, right_now).get_prev(datetime)
            self.assertEqual(base_date, prev_period if task.history[-1].completed_at < prev_period else task.history[-1].completed_at)
            # LinearDynamic should use this base date
            stress = task.get_rendered_stress()
            self.assertGreater(stress, 5)

if __name__ == "__main__":
    unittest.main()
