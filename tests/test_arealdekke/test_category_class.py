import unittest
from unittest.mock import MagicMock, patch

from generalization.n10.arealdekke.orchestrator.category_class import Category


class test_category_class(unittest.TestCase):

    def test_process_category(self) -> None:

        module = "generalization.n10.arealdekke.orchestrator.category_class"

        mock_sig = MagicMock()
        mock_sig.parameters.keys.return_value = ["input_fc", "output_fc"]

        with patch.object(Category, "set_cat_tools") as mock_cat_tools, patch(
            module + ".inspect.signature", return_value=mock_sig
        ), patch(module + ".arcpy.management.CopyFeatures") as mock_arcpy_copy:

            # A) What happens if the category has to start from the beginning?

            mock_cat_tools.return_value = {
                "simplify_and_smooth": MagicMock,
                "buff_small_segments": MagicMock,
                "test1": MagicMock,
                "test2": MagicMock,
            }

            cat_expected = Category(
                title="Elv",
                operations=["simplify_and_smooth", "buff_small_segments"],
                accessibility=True,
                order=1,
                map_scale="N10",
                last_processed=None,
                operations_completed=None,
                reinserts_completed=None,
            )

            operations_completed_test_A = 0

            for operation in cat_expected.process_category(
                input_fc="input", locked_fc="locked_fc", processed_fc="processed_fc"
            ):
                operations_completed_test_A += 1

            assert operations_completed_test_A == 2

            # B) What happens if the category has previously completed an operation but not all?

            cat_redone = Category(
                title="Innsjo",
                operations=[
                    "simplify_and_smooth",
                    "buff_small_segments",
                    "test1",
                    "test2",
                ],
                accessibility=True,
                order=2,
                map_scale="N10",
                last_processed="path",
                operations_completed=2,
                reinserts_completed=0,
            )

            operations_completed_test_B = 0

            for operation in cat_redone.process_category(
                input_fc="input", locked_fc="locked_fc", processed_fc="processed_fc"
            ):
                operations_completed_test_B += 1

            assert operations_completed_test_B == 2

            # C) What happens if all operations were previously completed?

            cat_completed = Category(
                title="Innsjo",
                operations=[
                    "simplify_and_smooth",
                    "buff_small_segments",
                    "test1",
                    "test2",
                ],
                accessibility=True,
                order=3,
                map_scale="N10",
                last_processed="path",
                operations_completed=4,
                reinserts_completed=2,
            )

            operations_completed_test_C = 0

            for operation in cat_completed.process_category(
                input_fc="input", locked_fc="locked_fc", processed_fc="processed_fc"
            ):
                operations_completed_test_C += 1

            assert operations_completed_test_C == 0
