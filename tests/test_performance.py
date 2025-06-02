import unittest
import time
import os
import json
from procrastitask.procrastitask_app import App
from procrastitask.task import Task
from unittest.mock import patch

class TestPerformance(unittest.TestCase):
    PERF_STATE_FILE = os.path.join(os.path.dirname(__file__), "perf_state.json")

    def _check_and_update_perf(self, test_name, current_runtime):
        # Load previous state
        try:
            with open(self.PERF_STATE_FILE, "r") as f:
                state = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            state = {}
        prev_runtime = state.get(test_name)
        if prev_runtime is not None:
            diff = (current_runtime - prev_runtime) / prev_runtime
            if diff > 0.25:
                self.fail(f"{test_name}: Runtime changed by more than 25% (prev: {prev_runtime:.4f}, curr: {current_runtime:.4f})")
        # Update state
        state[test_name] = current_runtime
        with open(self.PERF_STATE_FILE, "w") as f:
            json.dump(state, f)

    @patch("builtins.input", return_value="0")
    def test_main_path(self, _):
        start = time.time()
        app = App()
        app.load()
        app.list_all_tasks(also_print=False)
        duration = time.time() - start
        print(f"Total runtime: {duration:.4f} seconds")
        self._check_and_update_perf("test_main_path", duration)
        self.assertLess(duration, 5.0)

    def setUp(self):
        self.app = App()
        # Add some tasks for testing
        self.app.all_tasks = [
            Task(f"Task {i}", "desc", 1, 1, 1) for i in range(100)
        ]
        self.app.cached_listed_tasks = {i: t for i, t in enumerate(self.app.all_tasks)}

    @patch("builtins.input", return_value="0")
    def test_load_performance(self, mock_input):
        start = time.time()
        self.app.load(task_list_override=self.app.all_tasks)
        duration = time.time() - start
        print(f"App.load() runtime: {duration:.4f} seconds")
        self._check_and_update_perf("test_load_performance", duration)
        self.assertLess(duration, 1.0)  # Should be fast

    def test_list_all_tasks_performance(self):
        start = time.time()
        result = self.app.list_all_tasks(also_print=False)
        duration = time.time() - start
        print(f"App.list_all_tasks() runtime: {duration:.4f} seconds")
        self._check_and_update_perf("test_list_all_tasks_performance", duration)
        self.assertEqual(len(result), 100)
        self.assertLess(duration, 1.0)

    def test_task_to_dict_performance(self):
        task = self.app.all_tasks[0]
        start = time.time()
        for _ in range(1000):
            d = task.to_dict()
        duration = time.time() - start
        print(f"Task.to_dict() x1000 runtime: {duration:.4f} seconds")
        self._check_and_update_perf("test_task_to_dict_performance", duration)
        self.assertLess(duration, 1.0)

if __name__ == "__main__":
    unittest.main()
