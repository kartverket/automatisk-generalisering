import unittest
import tempfile
import yaml
import io
import os
from unittest.mock import patch
from generalization.n10.arealdekke.orchestrator.program_history_class import (
    Program_history_class as History_class,
)

# TO RUN TEST IN TERMINAL USE: & "C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -m pytest


class test_program_history_class(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        # Test data
        data_perfect: dict = {
            "newest_version": "path",
            "map_scale": "N10",
            "preprocessed": True,
            "preprocessing_operations_completed": 1,
            "category_history": [
                {
                    "title": "ElvFlate",
                    "operations": ["buff_small_segments", "simplify_and_smooth"],
                    "accessibility": True,
                    "order": 1,
                    "map_scale": "N10",
                    "last_processed": "path",
                    "operations_completed": 2,
                    "reinserts_completed": 0,
                },
                {
                    "title": "Innsjo",
                    "operations": ["buff_small_segments"],
                    "accessibility": True,
                    "order": 2,
                    "map_scale": "N10",
                    "last_processed": "path",
                    "operations_completed": 0,
                    "reinserts_completed": 0,
                },
            ],
        }

        data_non_processed: dict = {
            "newest_version": "path",
            "map_scale": "N10",
            "preprocessed": False,
            "preprocessing_operations_completed": 0,
            "category_history": [],
        }

        # Ideal file, temp saved
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as tmp_perfect:
            yaml.dump(data_perfect, tmp_perfect)
            tmp_perfect.close()
            self.tmp_path_perfect = tmp_perfect.name
            self.temp_file_perfect: History_class = History_class(self.tmp_path_perfect)

        # File where no preprocessings have occurred, temp saved
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as tmp_no_preprocess:
            yaml.dump(data_non_processed, tmp_no_preprocess)
            tmp_no_preprocess.close()
            self.temp_path_no_preprocess = tmp_no_preprocess.name
            self.temp_file_no_preprocess: History_class = History_class(
                self.temp_path_no_preprocess
            )

        # File path not exist
        self.non_existing_path = "test_non_exist_file.yml"
        self.temp_file_no_pre_exist: History_class = History_class(
            self.non_existing_path
        )

    def test_initiate(self):
        # What happens if the file is found
        self.assertEqual(self.temp_file_perfect.get_new_history_created(), False)
        self.assertEqual(self.temp_file_no_preprocess.get_new_history_created(), False)

        # What happens if the file is not found
        self.assertEqual(self.temp_file_no_pre_exist.get_new_history_created(), True)

    def test_restore_arealdekke_attributes(self):

        # What if the file already has values saved?
        goal_history_exists = {
            "file_path": "path",
            "map_scale": "N10",
            "preprocessed": True,
            "preprocessing_operations_completed": 1,
        }

        self.assertEqual(
            self.temp_file_perfect.restore_arealdekke_attributes(), goal_history_exists
        )

        # What if a new file was written?
        goal_history_non_preexisting = {}
        self.assertEqual(
            self.temp_file_no_pre_exist.restore_arealdekke_attributes(),
            goal_history_non_preexisting,
        )

        # What if no preprocessed operations were completed?
        self.assertEqual(
            self.temp_file_no_preprocess.restore_arealdekke_attributes(),
            goal_history_non_preexisting,
        )

    def test_restore_arealdekke_categories(self):
        # What happens if the categories have begun processing?
        response_perfect = self.temp_file_perfect.restore_arealdekke_categories()

        print(response_perfect)

        self.assertEqual(response_perfect["cats_exist"], True)
        self.assertEqual(len(response_perfect["cats"]), 2)

        # What happens if the categories have not begun processing?
        response_no_preprocess = (
            self.temp_file_no_preprocess.restore_arealdekke_categories()
        )
        self.assertEqual(response_no_preprocess["cats_exist"], False)

    def test_update_history_top_lvl(self):
        # What happens if we attempt to update a yml file that originally had much data?
        new_key_perfect = "preprocessed"
        new_value_perfect = True

        self.temp_file_perfect.update_history_top_lvl(
            new_key_perfect, new_value_perfect
        )
        self.assertEqual(
            self.temp_file_perfect.get_history_attribute_top_lvl(new_key_perfect),
            new_value_perfect,
        )

        # What happens if we attempt to update a yml file that was created from the template?
        new_key_non_exist = "last_processed"
        new_value_non_exist = "new_path"

        self.temp_file_no_pre_exist.update_history_top_lvl(
            new_key_non_exist, new_value_non_exist
        )
        self.assertEqual(
            self.temp_file_no_pre_exist.get_history_attribute_top_lvl(
                new_key_non_exist
            ),
            new_value_non_exist,
        )

    def test_update_history_cat_lvl(self):
        # What happens if we attempt to update a category that exist?
        new_key_perfect = "accessibility"
        new_value_perfect = False
        title_perfect = "ElvFlate"

        self.temp_file_perfect.update_history_cat_lvl(
            title=title_perfect, key=new_key_perfect, value=new_value_perfect
        )

        self.assertEqual(
            self.temp_file_perfect.get_history_attribute_cat_lvl(
                title=title_perfect, key=new_key_perfect
            ),
            new_value_perfect,
        )

        # What happens if we attempt to update a category that do not exist?
        new_key_non_exist = "accessibility"
        new_value_non_exist = False
        title_non_exist = "ElvFlate"

        self.temp_file_no_pre_exist.update_history_cat_lvl(
            title=title_non_exist, key=new_key_non_exist, value=new_value_non_exist
        )

        self.assertEqual(
            self.temp_file_no_pre_exist.get_history_attribute_cat_lvl(
                title=title_perfect, key=new_key_perfect
            ),
            None,
        )

    def test_new_history_category(self):
        # Test if we can add another category when processing have not started

        # Test if we can add another category after processing have begun.
        pass

    def tearDown(self):
        os.unlink(self.tmp_path_perfect)
        os.unlink(self.temp_path_no_preprocess)
        os.unlink(self.non_existing_path)

    @classmethod
    def tearDownClass(cls):
        pass
