import unittest
from procrastitask.procrastitask_app import App
from procrastitask.task import Task


class TestApp(unittest.TestCase):
    def test_can_initialize_app(self):
        App()

    def test_delete_task_by_idx_updates_dependent_on(self):
        app = App()
        task1 = Task("Task 1", "description", 1, 1, 1)
        task2 = Task("Task 2", "description", 1, 1, 1, dependent_on=[task1.identifier])
        task3 = Task("Task 3", "description", 1, 1, 1, dependent_on=[task1.identifier])
        
        app.all_tasks = [task1, task2, task3]
        app.cached_listed_tasks = {0: task1, 1: task2, 2: task3}
        
        app.delete_task_by_idx(0)
        
        self.assertNotIn(task1.identifier, task2.dependent_on)
        self.assertNotIn(task1.identifier, task3.dependent_on)
