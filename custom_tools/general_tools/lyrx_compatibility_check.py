import re
from typing import Protocol
import os
from file_manager import WorkFileManager
from composition_configs import core_config
import arcpy
from env_setup import environment_setup
import json
from custom_tools.general_tools import custom_arcpy
import uuid


import logging

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s: %(message)s",
)


logger = logging.getLogger(__name__)


class LyrxCompatibilityChecker:
    """
    Check each input feature against selected .lyrx definition queries and renderer.

    Fill in exactly one of layer name or data source to be used to select the appropriate layers from the .lyrx file.
    If lyrx file is only one layerDefinition both dataset and layer_name can be left empty.

    Attributes:
        lyrx_file (str): Path to the .lyrx file.
        feature_class_or_layer (str): Path to the input feature class or layer.
        wfm (WorkFileManager): Work file manager instance.
        dataset (str): Dataset name to select layers from the .lyrx file, (in lyrx file: LayerDefinition.featureTable.dataConnection.dataset)
        layer_name (list[str]): Layer name(s) to select layers from the .lyrx file, (in lyrx file: LayerDefinition.name)
    """

    def __init__(
        self,
        lyrx_file: str,
        feature_class_or_layer: str,
        wfm: WorkFileManager,
        dataset: str = "",
        layer_names: list[str | None] = [],
    ) -> None:
        logger.info(
            "Initializing LyrxCompatibilityChecker with lyrx_file: %s, feature_class_or_layer: %s",
            lyrx_file,
            feature_class_or_layer,
        )
        if sum(bool(value) for value in (dataset, layer_names)) > 1:
            raise ValueError(
                "Specify exactly one of data_source or layer_name, not both."
            )

        self.wfm = wfm
        self.lyrx_file = lyrx_file
        self.feature_class_or_layer = feature_class_or_layer
        self.dataset = dataset
        self.layer_names = layer_names
        self.layerfile = json.load(open(lyrx_file))
        self.selected_layers = self._selects_layers(self.layerfile)

    def convert_field_value(
        self, field_type: str, value: str
    ) -> str | int | float | None:
        if field_type == "String":
            return value
        if field_type in {"SmallInteger", "Integer", "BigInteger", "OID"}:
            return int(value)
        if field_type in {"Single", "Double"}:
            return float(value)
        raise ValueError(f"Unsupported renderer field type: {field_type}")

    def check_renderer(
        self, copied_features_layer: str, renderer: dict, definitionExpression: str
    ) -> bool:
        """Checks that all features in the copied layer matches a CIMUniqueValueClass in renderer."""
        logger.info("Checking renderer:")

        renderer_type = renderer.get("type")
        if renderer_type == "CIMSimpleRenderer":
            logger.info(
                "CIMSimpleRenderer detected which means all features selected by layer will match.\n"
            )
            arcpy.management.DeleteFeatures(copied_features_layer)
            return True

        if renderer_type != "CIMUniqueValueRenderer":
            logger.warning("Unsupported renderer type: %s", renderer_type)
            logger.warning(
                "Only CIMSimpleRenderer and CIMUniqueValueRenderer are supported by the LyrxCompatibilityChecker class."
            )
            raise ValueError(f"Unsupported renderer type: {renderer_type}")

        useDefaultSymbol = renderer.get("useDefaultSymbol")
        if useDefaultSymbol:
            logger.info(
                "Renderer uses default symbol which means all features selected by layer will match.\n"
            )
            arcpy.management.DeleteFeatures(copied_features_layer)
            return True

        feature_class_fields_type_map = {
            f.name: f.type for f in arcpy.ListFields(copied_features_layer)
        }

        fields = renderer.get("fields", [])
        groups = renderer.get("groups", [])

        if not fields or not groups:
            logger.warning("Renderer is missing fields or groups.\n")
            return False

        for group in groups:
            if group.get("type") == "CIMUniqueValueGroup":
                classes = group.get("classes", [])
                if not classes:
                    logger.warning("Group is missing classes.\n")
                    return False

                for cls in classes:
                    values = cls.get("values", [])
                    for value in values:
                        if value.get("type") == "CIMUniqueValue":
                            arcpy.management.SelectLayerByAttribute(
                                copied_features_layer,
                                "NEW_SELECTION",
                                definitionExpression,
                            )
                            fieldValues = value.get("fieldValues", [])

                            if not fieldValues:
                                logger.warning(
                                    "CIMUniqueValue is missing fieldValues.\n"
                                )
                                return False

                            if not len(fieldValues) == len(fields):
                                logger.warning(
                                    "Number of fieldValues does not match number of fields.\n"
                                )
                                return False

                            # logger.info(
                            #    "fields: %s", fields
                            # )
                            # logger.info(
                            #    "fieldValues: %s", fieldValues
                            # )
                            conditions = []
                            for field, field_value in zip(
                                fields, fieldValues, strict=True
                            ):
                                if field_value == "<Null>":
                                    conditions.append(f"{field} IS NULL")
                                else:
                                    field_value = self.convert_field_value(
                                        feature_class_fields_type_map[field],
                                        field_value,
                                    )
                                    conditions.append(f"{field} = '{field_value}'")

                            sql_expression = " AND ".join(conditions)
                            arcpy.management.SelectLayerByAttribute(
                                copied_features_layer,
                                "SUBSET_SELECTION",
                                sql_expression,
                            )
                            if (
                                int(arcpy.management.GetCount(copied_features_layer)[0])
                                > 0
                            ):
                                logger.info(
                                    "%s Total features match the CIMUniqueValue with unique values: %s",
                                    arcpy.management.GetCount(copied_features_layer)[0],
                                    fieldValues,
                                )
                            arcpy.management.DeleteFeatures(copied_features_layer)

        arcpy.management.SelectLayerByAttribute(
            copied_features_layer, "NEW_SELECTION", definitionExpression
        )
        if int(arcpy.management.GetCount(copied_features_layer)[0]) > 0:
            logger.warning(
                "%s features did not match any renderer class.\n",
                arcpy.management.GetCount(copied_features_layer)[0],
            )
            return False
        else:
            logger.info("All features matched at least one renderer class.\n")
            return True

    def check_compatibility(self) -> bool:
        """Return True if each input row matches a selected layer's definition expression and renderer"""
        logger.info(
            "Starting compatibility check for feature class or layer: %s",
            self.feature_class_or_layer,
        )

        if not self.selected_layers:
            logger.warning("No layers selected for compatibility check.")
            return False

        copied_features = self.wfm.build_file_path(
            f"lyrx_checker_input_copy_{uuid.uuid4().hex}", "gdb"
        )
        copied_features_layer = f"{copied_features}_layer"
        arcpy.management.CopyFeatures(self.feature_class_or_layer, copied_features)
        arcpy.management.MakeFeatureLayer(copied_features, copied_features_layer)

        layer_names = [layer.get("name") for layer in self.selected_layers]
        logger.info("Selected layers for compatibility check: %s\n", layer_names)

        for layer in self.selected_layers:
            logger.info("Checking compatibility for layer: %s", layer.get("name"))
            arcpy.management.SelectLayerByAttribute(
                copied_features_layer, "CLEAR_SELECTION"
            )
            featureTable = layer.get("featureTable", {})
            definitionExpression = featureTable.get("definitionExpression")
            renderer = layer.get("renderer", {})

            if definitionExpression:
                arcpy.management.SelectLayerByAttribute(
                    copied_features_layer, "NEW_SELECTION", definitionExpression
                )

            if int(arcpy.management.GetCount(copied_features_layer)[0]) == 0:
                logger.warning(
                    "No features match the definition query for layer: %s\n",
                    layer.get("name"),
                )
            else:
                logger.info(
                    "%s Total features match the definition query for layer: %s",
                    arcpy.management.GetCount(copied_features_layer)[0],
                    layer.get("name"),
                )

                self.check_renderer(
                    copied_features_layer, renderer, definitionExpression
                )

        arcpy.management.SelectLayerByAttribute(
            copied_features_layer, "CLEAR_SELECTION"
        )
        if int(arcpy.management.GetCount(copied_features_layer)[0]) > 0:
            logger.warning(
                "%s features did not match any selected layer's definition query.",
                arcpy.management.GetCount(copied_features_layer)[0],
            )
            self.wfm.delete_created_files(delete_targets=[copied_features])

            return False

        arcpy.management.Delete(copied_features_layer)
        self.wfm.delete_created_files(delete_targets=[copied_features])

        logger.info(
            "All features found a match in the selected layers' definition queries.\n"
        )
        return True

    def _selects_layers(self, layerfile):
        """
        Selects layers from the given layerfile based on the dataset, layer name, or object type specified in the instance.
        Returns a list of selected layer definitions.
        """
        layerdefinitions = layerfile.get("layerDefinitions", [])

        available_layers = set()

        selected_layers = []
        if self.dataset:
            for layerdef in layerdefinitions:
                layer_name = layerdef.get("name")
                feature_table = layerdef.get("featureTable", {})
                data_connection = feature_table.get("dataConnection", {})
                dataset = data_connection.get("dataset")
                available_layers.add(dataset)

                # logger.info("Layer name: %s", layer_name)
                # logger.info("Dataset: %s", dataset)
                if dataset == self.dataset:
                    selected_layers.append(layerdef)

            if not selected_layers:
                logger.warning("No layers matched input dataset: %s", self.dataset)
                logger.info("Datasets found in layers: %s", available_layers)

        elif self.layer_names:
            for layerdef in layerdefinitions:
                layer_name = layerdef.get("name")
                available_layers.add(layer_name)
                for input_name in self.layer_names:
                    if layer_name == input_name:
                        selected_layers.append(layerdef)

            if not selected_layers:
                logger.warning(
                    "No layers matched input layer name: %s", self.layer_names
                )
                logger.info("layer names found in layers: %s", available_layers)
        else:
            if len(layerdefinitions) == 1:
                selected_layers.append(layerdefinitions[0])
                logger.info("Only one layer definition found, selecting it by default.")
            else:
                raise ValueError(
                    "Multiple layer definitions found, but no dataset or layer name specified."
                )

        if selected_layers:
            logger.info(
                "Selected layers: %s\n",
                [layer.get("name") for layer in selected_layers],
            )

        return selected_layers
