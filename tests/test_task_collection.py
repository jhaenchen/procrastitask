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
        self.assertEquals(second_task, selected_task)

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
        self.assertEquals(second_task, selected_task)

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
        self.assertEquals([], selected_tasks)

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
        
