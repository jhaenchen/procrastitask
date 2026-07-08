import json
import os
import tempfile
import unittest
from unittest.mock import patch
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

    def test_relative_ranking_interleaves_lists(self):
        """
        With absolute ranking, a low-stress list is buried under a high-stress one.
        With relative ranking, the top of each list should appear first
        (both at percentile 1.0), then the bottoms.
        """
        app = App()
        work_high = Task("work-high", "d", 1, 1, 100, list_name="work")
        work_low = Task("work-low", "d", 1, 1, 90, list_name="work")
        home_high = Task("home-high", "d", 1, 1, 5, list_name="home")
        home_low = Task("home-low", "d", 1, 1, 1, list_name="home")
        app.all_tasks = [work_high, work_low, home_high, home_low]
        app.load(task_list_override=app.all_tasks)

        absolute = [t[1] for t in app.list_all_tasks(also_print=False, ranking="absolute")]
        relative = [t[1] for t in app.list_all_tasks(also_print=False, ranking="relative")]

        self.assertEqual(
            absolute,
            [work_high.identifier, work_low.identifier, home_high.identifier, home_low.identifier],
        )
        # Relative: both list-toppers first (tie at percentile 1.0), then both list-bottoms.
        # Within each tie, secondary sort by absolute stress puts the higher-stress one first.
        self.assertEqual(relative[0], work_high.identifier)
        self.assertEqual(relative[1], home_high.identifier)
        self.assertEqual(relative[2], work_low.identifier)
        self.assertEqual(relative[3], home_low.identifier)

    def test_relative_ranking_matches_absolute_within_single_list(self):
        app = App()
        t1 = Task("a", "d", 1, 1, 10, list_name="only")
        t2 = Task("b", "d", 1, 1, 20, list_name="only")
        t3 = Task("c", "d", 1, 1, 30, list_name="only")
        app.all_tasks = [t1, t2, t3]
        app.load(task_list_override=app.all_tasks)

        absolute = [t[1] for t in app.list_all_tasks(also_print=False, ranking="absolute")]
        relative = [t[1] for t in app.list_all_tasks(also_print=False, ranking="relative")]

        self.assertEqual(absolute, relative)

    def test_compute_relative_stress_ranks_ties_and_singletons(self):
        app = App()
        t1 = Task("t1", "d", 1, 1, 5, list_name="a")
        t2 = Task("t2", "d", 1, 1, 5, list_name="a")
        t3 = Task("t3", "d", 1, 1, 10, list_name="a")
        t_solo = Task("solo", "d", 1, 1, 42, list_name="b")
        app.all_tasks = [t1, t2, t3, t_solo]

        ranks = app.compute_relative_stress_ranks(app.all_tasks)

        # Singleton cohort → percentile 1.0
        self.assertEqual(ranks[t_solo.identifier], 1.0)
        # Ties get average rank; t1 and t2 share the bottom two ranks (0, 1) → avg 0.5 / 2 = 0.25
        self.assertEqual(ranks[t1.identifier], 0.25)
        self.assertEqual(ranks[t2.identifier], 0.25)
        # t3 is top of its cohort → 1.0
        self.assertEqual(ranks[t3.identifier], 1.0)


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


class TestListNameValidator(unittest.TestCase):
    def setUp(self):
        self.app = App()

    def test_valid_list_name_is_accepted(self):
        """Test that a list name in the config is accepted"""
        # The app should have loaded list_config.json with valid lists
        validator = self.app.list_name_validator
        # Assuming "default" is in the config
        result = validator("default")
        self.assertEqual(result, "default")

    def test_invalid_list_name_raises_error(self):
        """Test that an invalid list name raises ValueError"""
        validator = self.app.list_name_validator
        with self.assertRaises(ValueError) as context:
            validator("non_existent_list")
        self.assertIn("Invalid list name", str(context.exception))

    def test_empty_list_name_defaults_to_default(self):
        """Test that empty string defaults to 'default'"""
        validator = self.app.list_name_validator
        result = validator("")
        self.assertEqual(result, "default")

    def test_none_list_name_defaults_to_default(self):
        """Test that None defaults to 'default'"""
        validator = self.app.list_name_validator
        result = validator(None)
        self.assertEqual(result, "default")


class TestSave(unittest.TestCase):
    def test_save_deduplicates_tasks_by_identifier(self):
        app = App()
        task = Task("Beard trim", "", 4, 20, 4)
        duplicate = Task.from_dict(task.to_dict())
        app.all_tasks = [task, duplicate]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            tmp_path = f.name
        try:
            with patch.object(app, 'get_db_location', return_value=tmp_path):
                app.save()
            with open(tmp_path) as f:
                saved = json.load(f)
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0]['identifier'], task.identifier)
        finally:
            os.unlink(tmp_path)
