"""Tests for the round-robin shallow-bisect refresh flow."""
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from procrastitask.procrastitask_app import App
from procrastitask.task import Task
from procrastitask.dynamics.linear_dynamic import LinearDynamic
from procrastitask.dynamics.combined_dynamic import CombinedDynamic
from procrastitask.dynamics.static_offset_dynamic import StaticOffsetDynamic


def _mk(title, stress, list_name="L", last_refreshed_days_ago=0, dyn=None):
    t = Task(title, "d", 1, 1, stress, list_name=list_name)
    t.last_refreshed = datetime.now() - timedelta(days=last_refreshed_days_ago)
    if dyn is not None:
        t.stress_dynamic = dyn
    return t


def _app_with(tasks):
    app = App()
    app.all_tasks = tasks
    return app


def _run_refresh(app, oracle_fn):
    """Run refresh_stress_levels with:
      - stdout spied for [1]/[2] title lines, exposed via `state`
      - oracle_fn(state) called each prompt to produce "1"/"2"/"s"/"x"
    Returns the state dict with .item_titles, .b_titles, .q_count.
    """
    state = {"item": None, "b": None, "item_titles": [], "b_titles": [], "q": 0}
    orig_print = print

    def spy(*args, **kw):
        orig_print(*args, **kw)
        if args and isinstance(args[0], str):
            if args[0].startswith("  [1] "):
                state["item"] = args[0][len("  [1] "):]
            elif args[0].startswith("  [2] "):
                state["b"] = args[0][len("  [2] "):]

    def answer(_prompt):
        state["q"] += 1
        state["item_titles"].append(state["item"])
        state["b_titles"].append(state["b"])
        return oracle_fn(state)

    with patch("builtins.print", spy), \
         patch.object(app, "_prompt_bisect_answer", answer), \
         patch.object(app, "reset_screen", lambda: None), \
         patch.object(app, "save", lambda: None), \
         patch.object(app, "should_do_refresh", lambda: True):
        app.refresh_stress_levels()
    return state


class TestRoundRobinRefresh(unittest.TestCase):
    def test_full_run_sorts_cohort_by_user_preferences(self):
        # True preference: alphabetical by title (a least important, e most).
        tasks = [
            _mk("a", 50.0),
            _mk("b", 10.0),
            _mk("c", 90.0),
            _mk("d", 30.0),
            _mk("e", 70.0),
        ]
        app = _app_with(tasks)
        rank = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4}

        def oracle(state):
            return "1" if rank[state["item"]] > rank[state["b"]] else "2"

        _run_refresh(app, oracle)

        ranked = sorted(app.all_tasks, key=lambda t: t.get_rendered_stress(app.all_tasks))
        self.assertEqual([t.title for t in ranked], ["a", "b", "c", "d", "e"])

    def test_first_pass_touches_each_item_before_second_question(self):
        tasks = [_mk(f"t{i}", float(i * 10)) for i in range(1, 7)]
        app = _app_with(tasks)

        def oracle(state):
            if state["q"] >= 6:
                return "x"
            return "1"

        state = _run_refresh(app, oracle)
        # First 6 questions should touch 6 distinct items (breadth-first).
        self.assertEqual(len(set(state["item_titles"][:6])), 6)

    def test_bail_only_moves_touched_items(self):
        tasks = [_mk(f"t{i}", float(i * 10)) for i in range(1, 7)]
        app = _app_with(tasks)
        before = {t.identifier: t.get_rendered_stress(app.all_tasks) for t in tasks}

        def oracle(state):
            if state["q"] >= 3:
                return "x"
            return "1"

        state = _run_refresh(app, oracle)
        touched = set(state["item_titles"])
        for t in tasks:
            if t.title not in touched:
                self.assertAlmostEqual(
                    t.get_rendered_stress(app.all_tasks),
                    before[t.identifier],
                    places=6,
                )

    def test_skip_collapses_window_and_continues(self):
        tasks = [_mk(f"t{i}", float(i * 10)) for i in range(1, 5)]
        app = _app_with(tasks)

        def oracle(state):
            if state["q"] == 1:
                return "s"  # skip first item we see
            if state["q"] >= 20:
                return "x"
            return "1"

        state = _run_refresh(app, oracle)
        skipped = state["item_titles"][0]
        self.assertNotIn(skipped, state["item_titles"][1:])

    def test_first_asked_is_highest_priority_item(self):
        # stale + crowded beats fresh + isolated.
        stale_crowded = _mk("stale_crowded", 20.0, last_refreshed_days_ago=60)
        neighbor = _mk("neighbor", 20.1, last_refreshed_days_ago=0)
        fresh_isolated = _mk("fresh_isolated", 100.0, last_refreshed_days_ago=0)
        app = _app_with([stale_crowded, neighbor, fresh_isolated])

        def oracle(state):
            return "x"  # bail immediately after first prompt

        state = _run_refresh(app, oracle)
        self.assertEqual(state["item_titles"][0], "stale_crowded")

    def test_dynamic_preserved_through_writeback(self):
        dyn = LinearDynamic(interval=1.0)
        anchor = _mk("anchor", 10.0, dyn=dyn, last_refreshed_days_ago=60)
        others = [_mk(f"o{i}", float(i * 20)) for i in range(1, 5)]
        app = _app_with([anchor] + others)

        # Drive anchor repeatedly to the top ('1' always).
        def oracle(state):
            return "1"

        _run_refresh(app, oracle)

        # LinearDynamic must still be reachable.
        if isinstance(anchor.stress_dynamic, CombinedDynamic):
            self.assertTrue(any(isinstance(d, LinearDynamic) for d in anchor.stress_dynamic.dynamics))
            self.assertTrue(any(isinstance(d, StaticOffsetDynamic) for d in anchor.stress_dynamic.dynamics))
        else:
            self.assertIsInstance(anchor.stress_dynamic, LinearDynamic)

    def test_bs_last_refreshed_advanced_for_touched(self):
        tasks = [_mk(f"t{i}", float(i * 10), last_refreshed_days_ago=30) for i in range(1, 5)]
        app = _app_with(tasks)
        before = {t.identifier: t.last_refreshed for t in tasks}

        def oracle(state):
            return "1"

        _run_refresh(app, oracle)

        advanced = sum(1 for t in tasks if t.last_refreshed > before[t.identifier])
        # Full convergence touches every item many times; expect ≥ n-1.
        self.assertGreaterEqual(advanced, len(tasks) - 1)


if __name__ == "__main__":
    unittest.main()
