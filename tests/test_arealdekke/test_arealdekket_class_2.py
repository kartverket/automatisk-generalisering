import unittest
import tempfile
import yaml
import os
from pathlib import Path
from unittest.mock import patch
from generalization.n10.arealdekke.orchestrator.arealdekke_class import Arealdekke
from generalization.n10.arealdekke.orchestrator.program_history_class import Program_history_class as History_class

# TO RUN TEST IN TERMINAL USE: & "C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -m pytest

class test_arealdekket_class_2(unittest.TestCase):

    def setUp(self):
        #Mock the yml file and filepath
        data_pre_comp: dict = {
            "newest_version": "path",
            "map_scale": "N10",
            "preprocessed": True,
            "preprocessing_operations_completed": 1,
            "category_history":[
                {
                    "title": "ElvFlate",
                    "operations": [
                        "buff_small_segments",
                        "simplify_and_smooth"
                    ],
                    "accessibility": True,
                    "order": 1,
                    "map_scale": "N10",
                    "last_processed": "path",
                    "operations_completed": 2
                },
                {
                    "title": "Innsjo",
                    "operations": [
                        "buff_small_segments"
                    ],
                    "accessibility": True,
                    "order": 2,
                    "map_scale": "N10",
                    "last_processed": "path",
                    "operations_completed": 0
                }
            ]
        }

        data_pre_incomp: dict = {
            "newest_version": "path",
            "map_scale": "N10",
            "preprocessed": False,
            "preprocessing_operations_completed": 0,
            "category_history":[]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as temp_pre_comp:
            yaml.dump(data_pre_comp, temp_pre_comp)
            temp_pre_comp.close()
            self.temp_path_pre_comp = temp_pre_comp.name
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as temp_pre_incomp:
            yaml.dump(data_pre_incomp, temp_pre_incomp)
            temp_pre_incomp.close()
            self.temp_path_pre_incomp = temp_pre_incomp.name

        self.temp_path_non_existing="temp_file_path_non_existing.yml"

    def test_init(self):

        arealdekke_module="generalization.n10.arealdekke.orchestrator.arealdekke_class"
        history_module="generalization.n10.arealdekke.orchestrator.program_history_class"
        
        # Does arealdekke initiate correctly if the yml file is empty?
        with patch(history_module) as mock_pre_comp:
            
            mock_pre_comp.side_effect = lambda file_path : History_class(file_path=Path(self.temp_path_pre_comp))
            arealdekke_pre_comp = Arealdekke("N10")

            self.assertEqual(arealdekke_pre_comp.__str__(), "preprocessed: True preprocessings completed: 1 map scale: N10")

        
        # Does arealdekke initiate correctly if it previously completed the preprocessing?
        # What if arealdekke loaded in all info but stopped before the first preprocessing was done?
        
        '''
        with patch(history_module) as mock_pre_comp, patch(arealdekke_module+".arcpy") as mock_arcpy:
            
            mock_pre_comp.side_effect = lambda file_path : History_class(file_path=self.temp_path_pre_comp)
            arealdekke_pre_comp = Arealdekke("n10")
            mock_arcpy.management.CopyFeatures.assert_called_once()'''

        pass

    def tearDown(self):
        #Tear down the mocked yml files
            os.unlink(self.temp_path_pre_comp)
            os.unlink(self.temp_path_pre_incomp)