import unittest
from datetime import datetime
from procrastitask.dynamics.location_dynamic import LocationDynamic
from procrastitask.task import Task

class TestLocationDynamic(unittest.TestCase):

    def setUp(self):
        self.base_stress = 100
        self.latitude = 88.222
        self.longitude = -19.222
        self.radius = 1000
        self.dynamic = LocationDynamic(
            latitude=self.latitude,
            longitude=self.longitude,
            radius=self.radius
        )
        self.base_task = Task(title="Test Task", description="Test Description", difficulty=1, duration=1, stress=self.base_stress)

    def test_apply_within_radius(self):
        with unittest.mock.patch('procrastitask.location.get_location', return_value="88.222,-19.222"):
            new_stress = self.dynamic.apply(datetime.now(), self.base_stress, self.base_task)
            expected_stress = self.base_stress * 2
            self.assertEqual(new_stress, expected_stress)

    def test_apply_outside_radius(self):
        with unittest.mock.patch('procrastitask.location.get_location', return_value="0.0,0.0"):
            new_stress = self.dynamic.apply(datetime.now(), self.base_stress, self.base_task)
            self.assertEqual(new_stress, self.base_stress)

    def test_apply_null_location(self):
        with unittest.mock.patch('procrastitask.location.get_location', return_value=None):
            new_stress = self.dynamic.apply(datetime.now(), self.base_stress, self.base_task)
            self.assertEqual(new_stress, self.base_stress)

    def test_from_text_with_coordinates(self):
        text = "location/88.222/-19.222/1000"
        dynamic = LocationDynamic.from_text(text)
        self.assertEqual(dynamic.latitude, 88.222)
        self.assertEqual(dynamic.longitude, -19.222)
        self.assertEqual(dynamic.radius, 1000)

    def test_from_text_with_name(self):
        text = "location/houston/1000"
        dynamic = LocationDynamic.from_text(text)
        self.assertEqual(dynamic.latitude, 88.222)
        self.assertEqual(dynamic.longitude, -19.222)
        self.assertEqual(dynamic.radius, 1000)

    def test_to_text(self):
        text = self.dynamic.to_text()
        expected_text = f"dynamic-location/{self.latitude}/{self.longitude}/{self.radius}"
        self.assertEqual(text, expected_text)

if __name__ == "__main__":
    unittest.main()
