import unittest
from datetime import datetime, timedelta
from procrastitask.dynamics.absolute_linear_dynamic import AbsoluteLinearDynamic

class TestAbsoluteLinearDynamic(unittest.TestCase):
    def test_apply_increases_correctly(self):
        creation = datetime.now() - timedelta(days=10)
        dyn = AbsoluteLinearDynamic(increase_by=2, every_x_days=5)
        # 10 days = 2 increments, so +4
        self.assertAlmostEqual(dyn.apply(creation, 1, None), 5, places=2)

    def test_apply_fractional(self):
        creation = datetime.now() - timedelta(days=2.5)
        dyn = AbsoluteLinearDynamic(increase_by=4, every_x_days=5)
        # 2.5/5 = 0.5 increments, so +2
        self.assertAlmostEqual(dyn.apply(creation, 0, None), 2, places=2)

    def test_to_text_and_from_text(self):
        dyn = AbsoluteLinearDynamic(increase_by=3, every_x_days=7)
        text = dyn.to_text()
        self.assertTrue(text.startswith("dynamic-linear."), text)
        dyn2 = AbsoluteLinearDynamic.from_text(text)
        self.assertEqual(dyn2.increase_by, 3)
        self.assertEqual(dyn2.every_x_days, 7)

    def test_from_text_short(self):
        text = "linear.1.5-2.5"
        dyn = AbsoluteLinearDynamic.from_text(text)
        self.assertEqual(dyn.increase_by, 1.5)
        self.assertEqual(dyn.every_x_days, 2.5)

    def test_to_and_from_text_valid(self):
        dyn = AbsoluteLinearDynamic(increase_by=1.5, every_x_days=2.5)
        text = dyn.to_text()
        self.assertTrue(text.startswith("dynamic-linear."))
        dyn2 = AbsoluteLinearDynamic.from_text(text)
        self.assertEqual(dyn2.increase_by, 1.5)
        self.assertEqual(dyn2.every_x_days, 2.5)

    def test_invalid_text(self):
        with self.assertRaises(ValueError):
            AbsoluteLinearDynamic.from_text("linear.1.5")

if __name__ == "__main__":
    unittest.main()
