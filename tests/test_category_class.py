import unittest
import tempfile
import yaml
from unittest.mock import patch, MagicMock
from generalization.n10.arealdekke.orchestrator.category_class import Category


class test_category_class(unittest.TestCase):

    def test_process_category_t1(self):
        mock_operation = MagicMock(return_value=True)

        # Mock the dict so any key lookup returns mock_operation
        mock_cat_tools = MagicMock()
        mock_cat_tools.__getitem__ = MagicMock(return_value=mock_operation)
        mock_cat_tools.keys = MagicMock(return_value=["buff_small_segments"])

        with patch("generalization.n10.arealdekke.orchestrator.category_class.arcpy"):

            self.category_t1 = Category(
                "Ferskvann", ["buff_small_segments"], True, 1, "N10"
            )

            # Override the instance dict with the mock dict
            self.category_t1.cat_tools = mock_cat_tools

            with patch(
                "generalization.n10.arealdekke.orchestrator.category_class.arcpy"
            ):
                reinsert = self.category_t1.process_category(
                    "input_data", "locked_layers", "processed_lyr"
                )

                mock_operation.assert_called_once()
                self.assertTrue(reinsert)

    def tearDown(self):
        MagicMock.return_value = MagicMock()
