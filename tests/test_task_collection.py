from datetime import datetime, timedelta
import unittest
from procrastitask.dynamics.linear_dynamic import LinearDynamic
from procrastitask.task import Task
from procrastitask.task_collection import TaskCollection
from freezegun import freeze_time


class TestTaskCollection(unittest.TestCase):
    def test_get_n_last_completed_returns_correct_records(self):
        basic_task = Task("default title", "default descr", 10,10, 10)

        first_task = Task.from_dict(basic_task.to_dict())
        first_task.title = "first"
        first_task.complete()

        second_task = Task.from_dict(basic_task.to_dict())
        second_task.title = "second"
        second_task.complete()

        third_task = Task.from_dict(basic_task.to_dict())
        third_task.title = "third"

        full_task_collection = [first_task, second_task, third_task]

        collection = TaskCollection(filtered_tasks=full_task_collection, unfiltered_tasks=full_task_collection)
        selected_task = collection.get_n_last_completed_tasks(how_many_tasks=1)[0]
        # In this case, we asked for one, so we should get only the most recently completed task
        self.assertEqual(second_task, selected_task)

    def test_get_recently_completed_returns_correct_records(self):
        basic_task = Task("default title", "default descr", 10,10, 10)

        first_task = Task.from_dict(basic_task.to_dict())
        first_task.title = "first"
        first_task.complete()

        second_task = Task.from_dict(basic_task.to_dict())
        second_task.title = "second"
        second_task.complete()

        third_task = Task.from_dict(basic_task.to_dict())
        third_task.title = "third"

        full_task_collection = [first_task, second_task, third_task]

        collection = TaskCollection(filtered_tasks=full_task_collection, unfiltered_tasks=full_task_collection)
        selected_task = collection.get_recently_completed_tasks(how_many_results=1)[0]
        # In this case, we asked for one, so we should get only the most recently completed task
        self.assertEqual(second_task, selected_task)

    def test_get_recently_completed_handles_none_complete_within_range(self):
        basic_task = Task("default title", "default descr", 10,10, 10)

        searching_within = timedelta(weeks=1)

        first_task = Task.from_dict(basic_task.to_dict())
        first_task.title = "first"
        first_task.complete()
        # Completed too long ago
        first_task.history[0].completed_at = datetime.now() - (searching_within * 2)

        second_task = Task.from_dict(basic_task.to_dict())
        second_task.title = "second"

        third_task = Task.from_dict(basic_task.to_dict())
        third_task.title = "third"

        full_task_collection = [first_task, second_task, third_task]

        collection = TaskCollection(filtered_tasks=full_task_collection, unfiltered_tasks=full_task_collection)
        selected_tasks = collection.get_recently_completed_tasks(how_many_results=1, recent_is=searching_within)
        # Two incomplete, one too long ago
        self.assertEqual([], selected_tasks)

    def test_velocities_by_list_counts_recurring_task_completions(self):
        """Recurring tasks are incomplete but have completion history — should count toward velocity."""
        basic_task = Task("recurring", "descr", 10, 10, 10)
        basic_task.list_name = "work"
        basic_task.complete()
        # Simulate it being reset (recurring): mark incomplete but keep history
        basic_task.is_complete = False

        collection = TaskCollection(filtered_tasks=[basic_task], unfiltered_tasks=[basic_task])
        velocities = collection.get_velocities_by_list(interval=timedelta(weeks=1))
        self.assertGreater(velocities["work"], 0)

    def test_historical_velocities_buckets_completions_by_week(self):
        """A completion 3 weeks ago should appear in week index 2 (0-indexed from oldest end after reversal),
        i.e. week_idx=3 in the raw list returned by get_historical_velocities_by_list."""
        basic_task = Task("old task", "descr", 10, 10, 10)
        basic_task.list_name = "work"
        basic_task.complete()
        # Move the completion to 3.5 weeks ago (falls in week_idx=3 bucket)
        basic_task.history[0].completed_at = datetime.now() - timedelta(weeks=3, days=3)

        collection = TaskCollection(filtered_tasks=[basic_task], unfiltered_tasks=[basic_task])
        history = collection.get_historical_velocities_by_list(weeks_back=8)
        work_history = history["work"]
        # week_idx=3 should be non-zero, current week (idx=0) should be zero
        self.assertEqual(work_history[0], 0.0)
        self.assertGreater(work_history[3], 0.0)

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

