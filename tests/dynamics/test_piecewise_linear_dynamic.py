import unittest
from datetime import datetime, timedelta
from freezegun import freeze_time

from procrastitask.task import Task
from procrastitask.dynamics.base_dynamic import BaseDynamic
from procrastitask.dynamics.piecewise_linear_dynamic import PiecewiseLinearDynamic


def _make_task(days_since_creation: float) -> Task:
    now = datetime.now()
    return Task(
        title="t",
        description="d",
        difficulty=1,
        duration=1,
        stress=1,
        creation_date=now - timedelta(days=days_since_creation),
        last_refreshed=now - timedelta(days=days_since_creation),
    )


class TestPiecewiseLinearDynamic(unittest.TestCase):
    def test_apply_interpolates_between_knots(self):
        right_now = datetime(2026, 1, 15, 12, 0)
        task = Task(
            title="t", description="d", difficulty=1, duration=1, stress=1,
            creation_date=right_now - timedelta(days=5),
            last_refreshed=right_now - timedelta(days=5),
        )
        dyn = PiecewiseLinearDynamic([(0, 0), (10, 100)])
        with freeze_time(right_now):
            self.assertAlmostEqual(dyn.apply(task.creation_date, 1, task), 50, places=2)

    def test_apply_clamps_before_first_knot(self):
        right_now = datetime(2026, 1, 15, 12, 0)
        task = Task(
            title="t", description="d", difficulty=1, duration=1, stress=1,
            creation_date=right_now,
            last_refreshed=right_now,
        )
        dyn = PiecewiseLinearDynamic([(5, 20), (10, 50)])
        with freeze_time(right_now):
            # day = 0, before first knot at day 5
            self.assertEqual(dyn.apply(task.creation_date, 1, task), 20)

    def test_apply_clamps_after_last_knot(self):
        right_now = datetime(2026, 1, 15, 12, 0)
        task = Task(
            title="t", description="d", difficulty=1, duration=1, stress=1,
            creation_date=right_now - timedelta(days=100),
            last_refreshed=right_now - timedelta(days=100),
        )
        dyn = PiecewiseLinearDynamic([(0, 0), (5, 50)])
        with freeze_time(right_now):
            self.assertEqual(dyn.apply(task.creation_date, 1, task), 50)

    def test_apply_single_knot_is_constant(self):
        right_now = datetime(2026, 1, 15, 12, 0)
        task = Task(
            title="t", description="d", difficulty=1, duration=1, stress=1,
            creation_date=right_now - timedelta(days=7),
            last_refreshed=right_now - timedelta(days=7),
        )
        dyn = PiecewiseLinearDynamic([(3, 42)])
        with freeze_time(right_now):
            self.assertEqual(dyn.apply(task.creation_date, 1, task), 42)

    def test_apply_multi_segment(self):
        right_now = datetime(2026, 1, 15, 12, 0)
        # knots at (0,10), (10,20), (20,60): at day 15, interpolate between (10,20) and (20,60) -> 40
        task = Task(
            title="t", description="d", difficulty=1, duration=1, stress=1,
            creation_date=right_now - timedelta(days=15),
            last_refreshed=right_now - timedelta(days=15),
        )
        dyn = PiecewiseLinearDynamic([(0, 10), (10, 20), (20, 60)])
        with freeze_time(right_now):
            self.assertAlmostEqual(dyn.apply(task.creation_date, 1, task), 40, places=2)

    def test_apply_floors_at_zero(self):
        right_now = datetime(2026, 1, 15, 12, 0)
        task = Task(
            title="t", description="d", difficulty=1, duration=1, stress=1,
            creation_date=right_now - timedelta(days=5),
            last_refreshed=right_now - timedelta(days=5),
        )
        dyn = PiecewiseLinearDynamic([(0, -20), (10, -5)])
        with freeze_time(right_now):
            self.assertEqual(dyn.apply(task.creation_date, 1, task), 0)

    def test_to_text_from_text_round_trip(self):
        dyn = PiecewiseLinearDynamic([(0, 10), (3, 30.5), (14, 80)])
        text = dyn.to_text()
        dyn2 = PiecewiseLinearDynamic.from_text(text)
        self.assertEqual(dyn2.knots, [(0, 10), (3, 30.5), (14, 80)])

    def test_init_sorts_knots(self):
        dyn = PiecewiseLinearDynamic([(10, 50), (0, 10), (5, 30)])
        self.assertEqual([k[0] for k in dyn.knots], [0, 5, 10])

    def test_find_dynamic_returns_piecewise_linear(self):
        found = BaseDynamic.find_dynamic("dynamic-piecewise.0:10;5:50")
        self.assertIsInstance(found, PiecewiseLinearDynamic)
        self.assertEqual(found.knots, [(0.0, 10.0), (5.0, 50.0)])

    def test_from_text_rejects_bad_format(self):
        with self.assertRaises(ValueError):
            PiecewiseLinearDynamic.from_text("nope")
        with self.assertRaises(ValueError):
            PiecewiseLinearDynamic.from_text("dynamic-piecewise.")
        with self.assertRaises(ValueError):
            PiecewiseLinearDynamic.from_text("dynamic-piecewise.0-10")

    def test_init_rejects_empty(self):
        with self.assertRaises(ValueError):
            PiecewiseLinearDynamic([])


if __name__ == "__main__":
    unittest.main()
