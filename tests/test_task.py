from datetime import datetime, timedelta
import unittest
from procrastitask.dynamics.combined_dynamic import CombinedDynamic
from procrastitask.dynamics.linear_dynamic import LinearDynamic
from procrastitask.dynamics.step_due_date_dynamic import StepDueDateDynamic
from procrastitask.dynamics.base_dynamic import BaseDynamic
from procrastitask.task import Task, TaskStatus, CompletionRecord
from freezegun import freeze_time
import pytest


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

    def make_task_with_cron(self, creation, cron, completions=None):
        t = Task(
            title="Test",
            description="desc",
            difficulty=1,
            duration=60,
            stress=1,
            due_date_cron=cron,
            creation_date=creation,
        )
        t.history = completions or []
        return t

    def test_no_completions_returns_first_due(self):
        creation = datetime(2025, 5, 20, 8, 0)
        cron = "0 8 * * *"  # every day at 8am
        task = self.make_task_with_cron(creation, cron)
        due = task.current_due_date
        self.assertIsNotNone(due)
        if due is not None:
            self.assertEqual(due.date(), datetime(2025, 5, 21, 8, 0).date())

    def test_one_completion_returns_second_due(self):
        creation = datetime(2025, 5, 20, 8, 0)
        cron = "0 8 * * *"
        first_due = datetime(2025, 5, 21, 8, 0)
        second_due = datetime(2025, 5, 22, 8, 0)
        comp = CompletionRecord(completed_at=first_due + timedelta(hours=1), stress_at_completion=1)
        task = self.make_task_with_cron(creation, cron, [comp])
        due = task.current_due_date
        self.assertIsNotNone(due)
        if due is not None:
            self.assertEqual(due.date(), second_due.date())

    def test_completion_before_due_still_counts(self):
        creation = datetime(2025, 5, 20, 8, 0)
        cron = "0 8 * * *"
        first_due = datetime(2025, 5, 21, 8, 0)
        comp = CompletionRecord(completed_at=first_due - timedelta(hours=2), stress_at_completion=1)
        task = self.make_task_with_cron(creation, cron, [comp])
        due = task.current_due_date
        self.assertIsNotNone(due)
        if due is not None:
            self.assertEqual(due.date(), datetime(2025, 5, 22, 8, 0).date())

    def test_fewer_completions_than_due_dates(self):
        creation = datetime(2025, 5, 19, 8, 0)
        cron = "0 8 * * *"
        # Due dates: 2025-05-20, 2025-05-21, 2025-05-22
        completions = [
            CompletionRecord(completed_at=datetime(2025, 5, 20, 9, 0), stress_at_completion=1),
            CompletionRecord(completed_at=datetime(2025, 5, 21, 7, 0), stress_at_completion=1),
        ]
        task = self.make_task_with_cron(creation, cron, completions)
        due = task.current_due_date
        self.assertIsNotNone(due)
        if due is not None:
            self.assertEqual(due.date(), datetime(2025, 5, 22, 8, 0).date())

    def test_more_completions_than_due_dates(self):
        creation = datetime(2025, 5, 20, 8, 0)
        cron = "0 8 * * *"
        # Only one due date before now, but two completions
        completions = [
            CompletionRecord(completed_at=datetime(2025, 5, 21, 8, 0), stress_at_completion=1),
            CompletionRecord(completed_at=datetime(2025, 5, 22, 8, 0), stress_at_completion=1),
        ]
        task = self.make_task_with_cron(creation, cron, completions)
        next_due = task.current_due_date
        self.assertIsNotNone(next_due)
        if next_due is not None:
            self.assertTrue(next_due > datetime.now())
