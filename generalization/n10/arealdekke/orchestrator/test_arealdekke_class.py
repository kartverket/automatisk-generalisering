import unittest
from unittest.mock import patch
import arealdekke_class

class test_arealdekke_class(unittest.TestCase):

    #Methods with this tag runs once everytime the tests are run.
    @classmethod
    def setUpClass(cls):
        print("setupClass")

    def setUp(self):
        pass

    def test_preprocess_and_add_categories(self):
        pass

    def tearDown(self):
        pass

    @classmethod
    def tearDownClass(cls):
        print("teardownClass")