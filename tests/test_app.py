import unittest
from procrastitask.procrastitask_app import App
from procrastitask.task import Task, TaskStatus
from datetime import datetime
from procrastitask.dynamics.static_offset_dynamic import StaticOffsetDynamic
from procrastitask.dynamics.combined_dynamic import CombinedDynamic
from procrastitask.dynamics.base_dynamic import BaseDynamic


class DummyDynamic(BaseDynamic):
    def apply(self, creation_date, base_stress, task):
        return base_stress

    def to_text(self):
        return "dummy"

    @staticmethod
    def from_text(text):
        return DummyDynamic()

    @property
    def prefixes(self):
        return ["dummy"]


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

    def test_list_all_tasks_returns_tasks_in_stress_order(self):
        app = App()
        task1 = Task("Task 1", "description", 1, 1, 1)
        task2 = Task("Task 2", "description", 1, 1, 2)
        task3 = Task("Task 3", "description", 1, 1, 3)
        app.all_tasks = [task1, task2, task3]
        app.load(task_list_override=app.all_tasks)

        result = app.list_all_tasks(also_print=False)

        self.assertEqual(result[0][1], task3.identifier)
        self.assertEqual(result[1][1], task2.identifier)


class TestModifyTaskStressByOffset(unittest.TestCase):
    def setUp(self):
        self.app = App()
        self.app.all_tasks = []
        self.app.cached_listed_tasks = {}

    def make_task(self, title="task", stress=10, dynamic=None):
        t = Task(
            title=title,
            description="",
            difficulty=1,
            duration=1,
            stress=stress,
            cool_down=None,
            creation_date=datetime.now(),
            last_refreshed=datetime.now(),
            stress_dynamic=dynamic,
        )
        self.app.all_tasks.append(t)
        idx = len(self.app.cached_listed_tasks)
        self.app.cached_listed_tasks[idx] = t
        return t, idx

    def test_add_static_offset_dynamic_if_none(self):
        t, idx = self.make_task()
        self.app.modify_cached_task_stress_by_offset(idx, 5)
        self.assertTrue(hasattr(t.stress_dynamic, 'offset'))
        self.assertEqual(getattr(t.stress_dynamic, 'offset', None), 5)

    def test_update_existing_static_offset_dynamic(self):
        t, idx = self.make_task(dynamic=StaticOffsetDynamic(3))
        self.app.modify_cached_task_stress_by_offset(idx, 2)
        self.assertTrue(hasattr(t.stress_dynamic, 'offset'))
        self.assertEqual(getattr(t.stress_dynamic, 'offset', None), 5)

    def test_add_static_offset_to_combined_dynamic(self):
        combined = CombinedDynamic([DummyDynamic()], operators=[])
        t, idx = self.make_task(dynamic=combined)
        self.app.modify_cached_task_stress_by_offset(idx, 4)
        found = [d for d in getattr(t.stress_dynamic, 'dynamics', []) if hasattr(d, 'offset')]
        self.assertTrue(found)
        self.assertEqual(getattr(found[0], 'offset', None), 4)

    def test_update_static_offset_in_combined_dynamic(self):
        static = StaticOffsetDynamic(2)
        combined = CombinedDynamic([DummyDynamic(), static], operators=["(+)"],)
        t, idx = self.make_task(dynamic=combined)
        self.app.modify_cached_task_stress_by_offset(idx, 3)
        found = [d for d in getattr(t.stress_dynamic, 'dynamics', []) if hasattr(d, 'offset')]
        self.assertTrue(found)
        self.assertEqual(getattr(found[0], 'offset', None), 5)

    def test_wrap_other_dynamic_in_combined(self):
        dummy = DummyDynamic()
        t, idx = self.make_task(dynamic=dummy)
        self.app.modify_cached_task_stress_by_offset(idx, 7)
        self.assertTrue(hasattr(t.stress_dynamic, 'dynamics'))
        found = [d for d in getattr(t.stress_dynamic, 'dynamics', []) if hasattr(d, 'offset')]
        self.assertTrue(found)
        self.assertEqual(getattr(found[0], 'offset', None), 7)

    def test_raises_if_task_not_found(self):
        with self.assertRaises(ValueError):
            self.app.modify_task_stress_by_offset("notfound", 1)
