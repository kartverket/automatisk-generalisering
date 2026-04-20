import unittest
import tempfile
import yaml
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from generalization.n10.arealdekke.orchestrator.arealdekke_class import Arealdekke
from generalization.n10.arealdekke.orchestrator.program_history_class import Program_history_class as History_class
from generalization.n10.arealdekke.orchestrator.category_class import Category

# TO RUN TEST IN TERMINAL USE: & "C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -m pytest

class test_arealdekket_class(unittest.TestCase):

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
                    "operations_completed": 0,
                    "reinserts_completed":0
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
                    "operations_completed": 0,
                    "reinserts_completed":0
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
            self.temp_obj_pre_comp = History_class(file_path=Path(self.temp_path_pre_comp))
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as temp_pre_incomp:
            yaml.dump(data_pre_incomp, temp_pre_incomp)
            temp_pre_incomp.close()
            self.temp_path_pre_incomp = temp_pre_incomp.name
            self.temp_obj_pre_incomp = History_class(file_path=Path(self.temp_path_pre_incomp))

        self.temp_path_non_existing="temp_file_path_non_existing.yml"

        self.arealdekke_module="generalization.n10.arealdekke.orchestrator.arealdekke_class"

    def test_init(self):

        # Does arealdekke initiate correctly if it previously completed the preprocessing?
        with patch(self.arealdekke_module + ".History_class") as mock_history_pre_comp:
            
            mock_history_pre_comp.return_value = self.temp_obj_pre_comp
            arealdekke_pre_comp = Arealdekke(map_scale="N10")

            self.assertEqual(arealdekke_pre_comp.__str__(), "preprocessed: True preprocessings completed: 1 map scale: N10")
        
        
        # What if arealdekke loaded in all info but stopped before the first preprocessing was done? (Would be the same if the yaml file was empty.)
        with patch(self.arealdekke_module + ".History_class") as mock_history_pre_incomp, \
            patch.object(History_class, "restore_arealdekke_attributes") as mock_restore:
            
            mock_history_pre_incomp.return_value = self.temp_obj_pre_incomp

            mock_restore.return_value = {
                "file_path": "/fake/path",
                "preprocessing_operations_completed": 0,
                "preprocessed": False,
                "map_scale": "N10",
            }

            arealdekke_pre_incomp = Arealdekke(map_scale="N10")

            self.assertEqual(arealdekke_pre_incomp.__str__(), "preprocessed: False preprocessings completed: 0 map scale: N10")

    def test_preprocess(self):

        # Does preprocess restart where it last stopped?
        temp_obj_pre_comp=Arealdekke.__new__(Arealdekke)
        temp_obj_pre_comp._Arealdekke__preprocessed=False
        temp_obj_pre_comp._Arealdekke__preprocessings_completed=2
        temp_obj_pre_comp._Arealdekke__map_scale="N10"
        temp_obj_pre_comp.categories=[]
        temp_obj_pre_comp.program_history=self.temp_obj_pre_comp
        temp_obj_pre_comp.files={"arealdekke_fc":"path"}

        fake_preprocesses=[MagicMock() for _ in range(10)]

        with patch(self.arealdekke_module + ".arcpy") as mock_arcpy, \
        patch(self.arealdekke_module + ".History_class") as mock_history_pre_comp, \
        patch.object(Arealdekke, "set_preprocesses", return_value=fake_preprocesses) as mock_preprocesses_lst:
            
            mock_arcpy.return_value = None
            temp_obj_pre_comp.program_history.update_history_top_lvl = MagicMock()

            temp_obj_pre_comp.preprocess()

            assert sum(preprocess.call_count for preprocess in fake_preprocesses) == 8
            self.assertEqual(temp_obj_pre_comp._Arealdekke__preprocessings_completed, 10)

    def test_get_locked_categories(self)->None:

        # What happens if we have four locked categories?
        temp_obj_with_locked=Arealdekke.__new__(Arealdekke)
        temp_obj_with_locked._Arealdekke__preprocessed=False
        temp_obj_with_locked._Arealdekke__preprocessings_completed=2
        temp_obj_with_locked._Arealdekke__map_scale="N10"
        temp_obj_with_locked.categories=[]
        temp_obj_with_locked.files={"arealdekke_fc":"path"}

        # What happens if we have no locked categories?

        pass

    def test_add_categories(self)->None:
        pass

    def test_process_categories(self)->None:
        
        # What happens if we run through the process as normal?
        with patch(self.arealdekke_module + ".History_class") as mock_history_pre_comp:
            
            mock_history_pre_comp.return_value = self.temp_obj_pre_comp
            arealdekke_pre_comp = Arealdekke(map_scale="N10")

            arealdekke_pre_comp.process_categories()

            for cat in arealdekke_pre_comp.categories:
                assert cat.get_accessibility()==False
                assert cat.get_reinserts_completed()==2



        # What happens if we previously fully completed all operations for one category but did not reinsert it?
        # What happens if we previously fully completed all opeations and reinsertions for one category?
        
        pass

    def tearDown(self):
        #Tear down the mocked yml files
            os.unlink(self.temp_path_pre_comp)
            os.unlink(self.temp_path_pre_incomp)