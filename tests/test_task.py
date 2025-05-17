from datetime import datetime, timedelta
import unittest
from procrastitask.dynamics.linear_dynamic import LinearDynamic
from procrastitask.task import Task, TaskStatus, CompletionRecord
from freezegun import freeze_time


class TestTask(unittest.TestCase):
    def test_cool_down_properly_bounces_to_incomplete(self):
        right_now = datetime.now()
        created_task = Task(
            "Test task",
            "description",
            10,
            10,
            stress=10,
            periodicity=None,
            stress_dynamic=None,
            creation_date=right_now,
            last_refreshed=right_now,
            cool_down="1hr"
        )
        with freeze_time(right_now):
            created_task.complete()
        self.assertTrue(created_task.is_complete)
        self.assertEqual(created_task.status, TaskStatus.COMPLETE)
        with freeze_time(right_now + timedelta(hours=1.1)):
            self.assertFalse(created_task.is_complete)
            self.assertEqual(created_task.status, TaskStatus.INCOMPLETE)

    def test_cron_stress_resets_at_interval_overlap(self):
        """
        When you have a repeating task with a stress dynamic, the stress should be based on the last 
        possible interval overlap rather than the last time you completed it.
        """
        right_now = datetime.now()
        base_stress = 10
        stress_added_per_day = 1
         # Each day of the week we increase by stress_added_per_day. After one week, it should go back down to 0 and start again.
        max_rendered_stress = base_stress + (7 * stress_added_per_day)
        created_task = Task(
            "Test task",
            "description",
            10,
            10,
            stress=base_stress,
            periodicity="0 0 * * 0", # Once a week at midnight
            stress_dynamic=LinearDynamic(stress_added_per_day),
            creation_date=right_now,
            last_refreshed=right_now,
        )
        with freeze_time(right_now):
            first_stress = created_task.get_rendered_stress()
        with freeze_time(right_now + timedelta(days=28)): # Now skip forward 4 weeks. The stress should be less than the maximum.
            second_stress = created_task.get_rendered_stress()
            self.assertLess(second_stress, max_rendered_stress)

    def test_set_task_in_progress(self):
        right_now = datetime.now()
        created_task = Task(
            "Test task",
            "description",
            10,
            10,
            stress=10,
            periodicity=None,
            stress_dynamic=None,
            creation_date=right_now,
            last_refreshed=right_now,
        )
        created_task.set_in_progress()
        self.assertEqual(created_task.status, TaskStatus.IN_PROGRESS)
        self.assertFalse(created_task.is_complete)

    def test_set_task_incomplete(self):
        right_now = datetime.now()
        created_task = Task(
            "Test task",
            "description",
            10,
            10,
            stress=10,
            periodicity=None,
            stress_dynamic=None,
            creation_date=right_now,
            last_refreshed=right_now,
        )
        created_task.set_in_progress()
        created_task.set_incomplete()
        self.assertEqual(created_task.status, TaskStatus.INCOMPLETE)
        self.assertFalse(created_task.is_complete)

    def test_is_complete_uses_most_recent_completion_time_from_history(self):
        right_now = datetime.now()
        created_task = Task(
            "Test task",
            "description",
            10,
            10,
            stress=10,
            periodicity=None,
            stress_dynamic=None,
            creation_date=right_now,
            last_refreshed=right_now,
            cool_down="1hr"
        )
        with freeze_time(right_now):
            created_task.complete()
        self.assertTrue(created_task.is_complete)
        self.assertEqual(created_task.status, TaskStatus.COMPLETE)
        with freeze_time(right_now + timedelta(hours=0.5)):
            created_task.complete()
        self.assertTrue(created_task.is_complete)
        self.assertEqual(created_task.status, TaskStatus.COMPLETE)
        with freeze_time(right_now + timedelta(hours=1.1)):
            self.assertFalse(created_task.is_complete)
            self.assertEqual(created_task.status, TaskStatus.INCOMPLETE)

    def test_is_complete_updates_history_with_completion_time(self):
        right_now = datetime.now()
        created_task = Task(
            "Test task",
            "description",
            10,
            10,
            stress=10,
            periodicity=None,
            stress_dynamic=None,
            creation_date=right_now,
            last_refreshed=right_now,
            cool_down="1hr"
        )
        with freeze_time(right_now):
            created_task.complete()
        self.assertEqual(len(created_task.history), 1)
        self.assertEqual(created_task.history[0].completed_at, right_now)
        self.assertEqual(created_task.history[0].stress_at_completion, 10)
        with freeze_time(right_now + timedelta(hours=0.5)):
            created_task.complete()
        self.assertEqual(len(created_task.history), 2)
        self.assertEqual(created_task.history[1].completed_at, right_now + timedelta(hours=0.5))
        self.assertEqual(created_task.history[1].stress_at_completion, 10)
