import unittest
import tempfile
import yaml
from unittest.mock import patch
from generalization.n10.arealdekke.orchestrator.arealdekke_class import Arealdekke

#TO RUN TEST IN TERMINAL USE: & "C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -m pytest

class test_arealdekke_class(unittest.TestCase):

    #Methods with this tag runs once everytime the tests are run.
    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        with patch("generalization.n10.arealdekke.orchestrator.arealdekke_class.arcpy") as mock_arcpy:
          mock_arcpy.management.CopyFeatures.return_value = "fake"
          self.arealdekke_t1=Arealdekke("path", "N10")
          self.arealdekke_t1.preprocessed=True

          cat_config="""
          Categories :
            - title : Ferskvann_elv_bekk
              operations :
                - buff_small_segments
              accessibility : true
              order: 1
              map_scale: N10
            - title : Ferskvann_innsjo_tjern
              operations :
                - buff_small_segments
              accessibility : true
              order: 2
              map_scale: N10
            - title : Ferskvann_innsjo_tjern_regulert
              operations :
                - remove_islands
              accessibility : true
              order: 3
              map_scale: N10
          """
        
        self.expected = yaml.safe_load(cat_config)["Categories"]

        #Then, we mock the yaml file
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp:
            tmp.write(cat_config)
            tmp_path = tmp.name

        self.arealdekke_t1.add_categories(categories_config_file=tmp_path)


    def test_add_categories(self):        
        for cat in self.arealdekke_t1.categories:
          for cat_test in self.expected:
            if cat.get_order()==cat_test["order"]:
              self.assertEqual(cat.get_title(), cat_test["title"])
              self.assertEqual(cat.get_accessibility(), cat_test["accessibility"])
              self.assertEqual(cat.get_operations(), cat_test["operations"])


    def tearDown(self):
        pass

    @classmethod
    def tearDownClass(cls):
        print("teardownClass")