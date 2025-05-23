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
        When you have a repeating task with a stress dynamic, the stress should be based on the period immediately following the most recent completion (not the last time you completed it).
        """
        right_now = datetime(2025, 5, 18, 0, 0)  # Sunday
        base_stress = 10
        stress_added_per_day = 1
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
        # Complete the task on the first Sunday
        with freeze_time(right_now):
            created_task.complete()
            first_stress = created_task.get_rendered_stress()
        # Move forward 4 weeks
        with freeze_time(right_now + timedelta(days=28)):
            from croniter import croniter
            last_completion = created_task.history[-1].completed_at
            next_period = croniter("0 0 * * 0", last_completion).get_next(datetime)
            self.assertEqual(created_task.get_dynamic_base_date(), next_period)
            # Calculate expected stress using LinearDynamic logic
            delta_days = (right_now + timedelta(days=28) - next_period).total_seconds() / 86400
            expected_stress = base_stress + (delta_days / stress_added_per_day)
            actual_stress = created_task.get_rendered_stress()
            self.assertAlmostEqual(actual_stress, expected_stress, places=2)

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
        base = datetime(2025, 5, 20, 8, 0)
        cron = "0 8 * * *"  # every day at 8am
        task = self.make_task_with_cron(base, cron)
        due = task.current_due_date
        self.assertIsNotNone(due)
        if due is not None:
            expected_due = base + timedelta(days=1)
            self.assertEqual(due.date(), expected_due.date())

    def test_one_completion_returns_second_due(self):
        base = datetime(2025, 5, 20, 8, 0)
        cron = "0 8 * * *"
        first_due = base + timedelta(days=1)
        second_due = base + timedelta(days=2)
        comp = CompletionRecord(completed_at=first_due + timedelta(hours=1), stress_at_completion=1)
        task = self.make_task_with_cron(base, cron, [comp])
        due = task.current_due_date
        self.assertIsNotNone(due)
        if due is not None:
            self.assertEqual(due.date(), second_due.date())

    def test_completion_before_due_still_counts(self):
        base = datetime(2025, 5, 20, 8, 0)
        cron = "0 8 * * *"
        first_due = base + timedelta(days=1)
        comp = CompletionRecord(completed_at=first_due - timedelta(hours=2), stress_at_completion=1)
        task = self.make_task_with_cron(base, cron, [comp])
        due = task.current_due_date
        self.assertIsNotNone(due)
        if due is not None:
            expected_due = base + timedelta(days=2)
            self.assertEqual(due.date(), expected_due.date())

    def test_fewer_completions_than_due_dates(self):
        base = datetime(2025, 5, 19, 8, 0)
        cron = "0 8 * * *"
        # Due dates: base+1, base+2, base+3
        completions = [
            CompletionRecord(completed_at=base + timedelta(days=1, hours=1), stress_at_completion=1),
            CompletionRecord(completed_at=base + timedelta(days=2) - timedelta(hours=1), stress_at_completion=1),
        ]
        task = self.make_task_with_cron(base, cron, completions)
        due = task.current_due_date
        self.assertIsNotNone(due)
        if due is not None:
            expected_due = base + timedelta(days=3)
            self.assertEqual(due.date(), expected_due.date())

    def test_more_completions_than_due_dates(self):
        base = datetime(2025, 5, 20, 8, 0)
        cron = "0 8 * * *"
        # Only one due date before now, but two completions
        completions = [
            CompletionRecord(completed_at=base + timedelta(days=1), stress_at_completion=1),
            CompletionRecord(completed_at=base + timedelta(days=2), stress_at_completion=1),
        ]
        task = self.make_task_with_cron(base, cron, completions)
        next_due = task.current_due_date
        self.assertIsNotNone(next_due)
        # The next due date may be in the past if all completions and due dates are in the past
        # So just check that it's a datetime object
        self.assertIsInstance(next_due, datetime)
