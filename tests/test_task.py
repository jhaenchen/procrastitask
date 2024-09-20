from datetime import datetime, timedelta
import unittest
from procrastitask.dynamics.linear_dynamic import LinearDynamic
from procrastitask.task import Task, TaskState
from freezegun import freeze_time


class TestTask(unittest.TestCase):
    def test_is_complete_follows_state_from_complete_to_incomplete(self):
        right_now = datetime.now()
        created_task = Task(
            "Test task",
            "description",
            10,
            10,
            stress=1,
            creation_date=right_now,
            last_refreshed=right_now,
        )
        created_task.complete()
        created_task.current_status = TaskState.QUEUED
        self.assertEqual(False, created_task.is_complete)
    
    def test_state_follows_is_complete_from_incomplete_to_complete(self):
        right_now = datetime.now()
        created_task = Task(
            "Test task",
            "description",
            10,
            10,
            stress=1,
            creation_date=right_now,
            last_refreshed=right_now,
        )
        created_task.current_status = TaskState.QUEUED
        created_task.complete()
        self.assertEqual(TaskState.COMPLETE, created_task.current_status)


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
        
