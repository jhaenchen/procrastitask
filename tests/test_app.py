import unittest
from procrastitask.procrastitask_app import App
from procrastitask.task import Task, TaskStatus


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

    def test_set_task_in_progress_via_command(self):
        app = App()
        task = Task("Task 1", "description", 1, 1, 1)
        app.all_tasks = [task]
        app.cached_listed_tasks = {0: task}
        
        app.display_home("q0")
        
        self.assertEqual(task.status, TaskStatus.IN_PROGRESS)

    def test_set_task_incomplete_via_command(self):
        app = App()
        task = Task("Task 1", "description", 1, 1, 1)
        task.set_in_progress()
        app.all_tasks = [task]
        app.cached_listed_tasks = {0: task}
        
        app.display_home("dq0")
        
        self.assertEqual(task.status, TaskStatus.INCOMPLETE)

    def test_view_in_progress_tasks(self):
        app = App()
        task1 = Task("Task 1", "description", 1, 1, 1)
        task2 = Task("Task 2", "description", 1, 1, 1)
        task2.set_in_progress()
        app.all_tasks = [task1, task2]
        app.load(task_list_override=app.all_tasks)
        
        in_progress_tasks = [t[1] for t in app.list_in_progress_tasks()]
        
        self.assertIn(task2.identifier, in_progress_tasks)
        self.assertNotIn(task1.identifier, in_progress_tasks)

    def test_list_all_tasks_returns_tuples_with_identifiers(self):
        app = App()
        task1 = Task("Task 1", "description", 1, 1, 1)
        task2 = Task("Task 2", "description", 1, 1, 1)
        app.all_tasks = [task1, task2]
        
        result = app.list_all_tasks(also_print=False)
        
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], tuple)
        self.assertEqual(result[0][1], task1.identifier)
        self.assertIsInstance(result[1], tuple)
        self.assertEqual(result[1][1], task2.identifier)

    def test_recently_created_command(self):
        app = App()
        task1 = Task("Task 1", "description", 1, 1, 1)
        task2 = Task("Task 2", "description", 1, 1, 1)
        task3 = Task("Task 3", "description", 1, 1, 1)
        app.all_tasks = [task1, task2, task3]
        app.load(task_list_override=app.all_tasks)
        
        app.display_home("recently created")
        
        recently_created_tasks = [t[1] for t in app.list_all_tasks()]
        
        self.assertEqual(len(recently_created_tasks), 3)
        self.assertEqual(recently_created_tasks[0], task3.identifier)
        self.assertEqual(recently_created_tasks[1], task2.identifier)
        self.assertEqual(recently_created_tasks[2], task1.identifier)
