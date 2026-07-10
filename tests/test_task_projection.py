import unittest
from datetime import datetime, timedelta
from freezegun import freeze_time

from procrastitask.task import Task
from procrastitask.task_projection import project_rendered_stress
from procrastitask.dynamics.linear_dynamic import LinearDynamic
from procrastitask.dynamics.piecewise_linear_dynamic import PiecewiseLinearDynamic


class TestProjectRenderedStress(unittest.TestCase):
    def test_no_dynamic_is_constant(self):
        right_now = datetime(2026, 6, 1, 12, 0)
        task = Task(
            title="constant", description="", difficulty=1, duration=1, stress=42,
            creation_date=right_now, last_refreshed=right_now,
        )
        with freeze_time(right_now):
            samples = project_rendered_stress(task, days_ahead=10, samples=6)
        stresses = [round(s, 2) for _, s in samples]
        self.assertEqual(stresses, [42.0] * 6)
        # day offsets are evenly spaced starting at 0
        self.assertAlmostEqual(samples[0][0], 0.0)
        self.assertAlmostEqual(samples[-1][0], 10.0)

    def test_linear_dynamic_grows_over_time(self):
        right_now = datetime(2026, 6, 1, 12, 0)
        # interval=1 → stress grows by 1/day
        task = Task(
            title="ramp", description="", difficulty=1, duration=1, stress=10,
            creation_date=right_now, last_refreshed=right_now,
            stress_dynamic=LinearDynamic(interval=1),
        )
        with freeze_time(right_now):
            samples = project_rendered_stress(task, days_ahead=10, samples=11)
        # Day 0 ≈ 10; day 10 ≈ 20; monotonically non-decreasing.
        self.assertAlmostEqual(samples[0][1], 10.0, places=1)
        self.assertAlmostEqual(samples[-1][1], 20.0, places=1)
        for a, b in zip(samples, samples[1:]):
            self.assertGreaterEqual(b[1] + 1e-6, a[1])

    def test_piecewise_linear_follows_knots(self):
        right_now = datetime(2026, 6, 1, 12, 0)
        # Knots: (0, 10), (10, 60), (20, 60) — should ramp then plateau.
        dyn = PiecewiseLinearDynamic([(0, 10), (10, 60), (20, 60)])
        task = Task(
            title="pw", description="", difficulty=1, duration=1, stress=1,
            creation_date=right_now, last_refreshed=right_now,
            stress_dynamic=dyn,
        )
        with freeze_time(right_now):
            samples = project_rendered_stress(task, days_ahead=20, samples=21)
        # At day 0: 10 (rounded)
        self.assertAlmostEqual(samples[0][1], 10.0, delta=0.15)
        # At day 5: 35 (midpoint of first segment)
        self.assertAlmostEqual(samples[5][1], 35.0, delta=0.15)
        # At day 10: 60
        self.assertAlmostEqual(samples[10][1], 60.0, delta=0.15)
        # At day 15 and day 20: still 60 (plateau)
        self.assertAlmostEqual(samples[15][1], 60.0, delta=0.15)
        self.assertAlmostEqual(samples[20][1], 60.0, delta=0.15)

    def test_samples_at_least_two(self):
        task = Task(title="x", description="", difficulty=1, duration=1, stress=1)
        with self.assertRaises(ValueError):
            project_rendered_stress(task, samples=1)

    def test_days_ahead_positive(self):
        task = Task(title="x", description="", difficulty=1, duration=1, stress=1)
        with self.assertRaises(ValueError):
            project_rendered_stress(task, days_ahead=0)


if __name__ == "__main__":
    unittest.main()
