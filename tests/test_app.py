
import unittest
from procrastitask.procrastitask import App


class TestApp(unittest.TestCase):
    def test_can_initialize_app(self):
        App()