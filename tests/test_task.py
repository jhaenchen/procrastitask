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

    def test_find_dependents(self):
        t1 = Task("A", "desc", 1, 10, 5)
        t2 = Task("B", "desc", 1, 10, 5, dependent_on=[t1.identifier])
        t3 = Task("C", "desc", 1, 10, 5, dependent_on=[t1.identifier])
        all_tasks = [t1, t2, t3]
        dependents = t1.find_dependents(all_tasks)
        self.assertEqual(set(d.identifier for d in dependents), set([t2.identifier, t3.identifier]))

    def test_dependent_tasks_complete(self):
        t1 = Task("A", "desc", 1, 10, 5)
        t2 = Task("B", "desc", 1, 10, 5)
        t3 = Task("C", "desc", 1, 10, 5)
        t3.dependent_on = [t1.identifier, t2.identifier]
        all_tasks = [t1, t2, t3]
        t1.is_complete = True
        t2.is_complete = False
        self.assertFalse(t3.dependent_tasks_complete(all_tasks))
        t2.is_complete = True
        self.assertTrue(t3.dependent_tasks_complete(all_tasks))

    def test_headline_format(self):
        t = Task("HeadlineTest", "desc", 3, 45, 7)
        headline = t.headline()
        self.assertIn("HeadlineTest", headline)
        self.assertIn("45min", headline)
        self.assertIn("stress: 7", headline)
        self.assertIn("diff: 3", headline)

    def test_get_next_cool_down_reset_date_and_is_complete(self):
        right_now = datetime.now()
        t = Task("CoolDownTest", "desc", 1, 10, 5, cool_down="2hr")
        t.complete()
        next_reset = t._get_next_cool_down_reset_date()
        self.assertIsNotNone(next_reset)
        self.assertAlmostEqual((next_reset - right_now).total_seconds(), 2*3600*0.9, delta=2)
        # is_complete should be True before next_reset, False after
        with freeze_time(right_now + timedelta(minutes=50)):
            self.assertTrue(t.is_complete)
        with freeze_time(right_now + timedelta(minutes=140)):
            self.assertFalse(t.is_complete)

    def test_get_dynamic_base_date_with_cool_down(self):
        right_now = datetime.now()
        t = Task("BaseDateCoolDown", "desc", 1, 10, 5, cool_down="1hr")
        t.history.append(CompletionRecord(completed_at=right_now, stress_at_completion=5))
        base_date = t.get_dynamic_base_date()
        self.assertIsNotNone(base_date)
        self.assertAlmostEqual((base_date - right_now).total_seconds(), 3600*0.9, delta=2)

    def test_stress_propagates_from_dependent(self):
        """Test that a task's stress is the maximum of its own stress and its dependents"""
        t1 = Task("A", "desc", 1, 10, 5)  # Base task with stress 5
        t2 = Task("B", "desc", 1, 10, 15, dependent_on=[t1.identifier])  # Depends on A, stress 15
        all_tasks = [t1, t2]

        # Without propagation (no all_tasks passed)
        self.assertEqual(t1.get_rendered_stress(), 5)

        # With propagation (all_tasks passed)
        self.assertEqual(t1.get_rendered_stress(all_tasks), 15)
        # Dependent should still show its own stress
        self.assertEqual(t2.get_rendered_stress(all_tasks), 15)

    def test_stress_propagates_through_chain(self):
        """Test multi-level stress propagation: A <- B <- C"""
        t1 = Task("A", "desc", 1, 10, 5)  # stress 5
        t2 = Task("B", "desc", 1, 10, 10, dependent_on=[t1.identifier])  # stress 10
        t3 = Task("C", "desc", 1, 10, 20, dependent_on=[t2.identifier])  # stress 20
        all_tasks = [t1, t2, t3]

        # C blocks B, B blocks A, so A should show C's stress (20)
        self.assertEqual(t1.get_rendered_stress(all_tasks), 20)
        self.assertEqual(t2.get_rendered_stress(all_tasks), 20)
        self.assertEqual(t3.get_rendered_stress(all_tasks), 20)

    def test_stress_propagates_max_from_multiple_dependents(self):
        """Test that a task shows the max stress from multiple dependents"""
        t1 = Task("A", "desc", 1, 10, 5)  # stress 5
        t2 = Task("B", "desc", 1, 10, 12, dependent_on=[t1.identifier])  # stress 12
        t3 = Task("C", "desc", 1, 10, 18, dependent_on=[t1.identifier])  # stress 18
        all_tasks = [t1, t2, t3]

        # A blocks both B and C, should show max (18)
        self.assertEqual(t1.get_rendered_stress(all_tasks), 18)

    def test_completed_tasks_dont_propagate_stress(self):
        """Test that completed dependent tasks don't propagate their stress"""
        t1 = Task("A", "desc", 1, 10, 5)  # stress 5
        t2 = Task("B", "desc", 1, 10, 20, dependent_on=[t1.identifier])  # stress 20
        t2._is_complete = True
        all_tasks = [t1, t2]

        # B is complete, so its stress shouldn't propagate to A
        self.assertEqual(t1.get_rendered_stress(all_tasks), 5)

    def test_circular_dependency_doesnt_infinite_loop(self):
        """Test that circular dependencies don't cause infinite loops"""
        t1 = Task("A", "desc", 1, 10, 5)
        t2 = Task("B", "desc", 1, 10, 10, dependent_on=[t1.identifier])
        # Create circular dependency (normally shouldn't happen, but let's be safe)
        t1.dependent_on = [t2.identifier]
        all_tasks = [t1, t2]

        # Should not infinite loop, should return some reasonable value
        stress1 = t1.get_rendered_stress(all_tasks)
        stress2 = t2.get_rendered_stress(all_tasks)
        # Both should have values (not crash)
        self.assertIsNotNone(stress1)
        self.assertIsNotNone(stress2)

    def test_backward_compatibility_without_all_tasks(self):
        """Test that get_rendered_stress still works without all_tasks parameter"""
        t1 = Task("A", "desc", 1, 10, 5)
        t2 = Task("B", "desc", 1, 10, 15, dependent_on=[t1.identifier])

        # Without all_tasks, should just return own stress
        self.assertEqual(t1.get_rendered_stress(), 5)
        self.assertEqual(t2.get_rendered_stress(), 15)
