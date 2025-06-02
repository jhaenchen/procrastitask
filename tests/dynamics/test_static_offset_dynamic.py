import unittest
from datetime import datetime
from procrastitask.dynamics.static_offset_dynamic import StaticOffsetDynamic
from procrastitask.task import Task

class DummyTask(Task):
    def __init__(self):
        # Provide minimal required fields for Task
        super().__init__(title="dummy", description="", difficulty=1, duration=1, stress=1, cool_down=None, creation_date=datetime.now(), last_refreshed=datetime.now(), stress_dynamic=None)

class TestStaticOffsetDynamic(unittest.TestCase):
    def test_apply(self):
        dyn = StaticOffsetDynamic(5)
        base_stress = 10
        creation_date = datetime.now()
        task = DummyTask()
        result = dyn.apply(creation_date, base_stress, task)
        self.assertEqual(result, 15)

    def test_to_text_and_from_text(self):
        dyn = StaticOffsetDynamic(7)
        text = dyn.to_text()
        self.assertEqual(text, "static-offset.7")
        dyn2 = StaticOffsetDynamic.from_text(text)
        self.assertIsInstance(dyn2, StaticOffsetDynamic)
        self.assertEqual(dyn2.offset, 7)

    def test_from_text_invalid(self):
        with self.assertRaises(ValueError):
            StaticOffsetDynamic.from_text("static-offset.7extra")
        with self.assertRaises(ValueError):
            StaticOffsetDynamic.from_text("static-offset.")
        with self.assertRaises(ValueError):
            StaticOffsetDynamic.from_text("static-offset.7.5")
        with self.assertRaises(ValueError):
            StaticOffsetDynamic.from_text("static-offset-seven")
        with self.assertRaises(ValueError):
            StaticOffsetDynamic.from_text("otherprefix.7")

    def test_prefixes(self):
        self.assertIn("static-offset.", StaticOffsetDynamic(0).prefixes)
