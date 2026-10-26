import re
from collections import Counter
from typing import Any, Protocol
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

NULL_VALUE = "<Null>"
REASON_FIELD = "lyrx_reason"
REASON_FIELD_LENGTH = 255
NO_DEFINITION_QUERY_MATCH = "NO_DEFINITION_QUERY_MATCH"
NO_RENDERER_CLASS = "NO_RENDERER_CLASS"
TOP_N_COMBINATIONS = 20


class LyrxCompatibilityChecker:
    """
    Check each input feature against selected .lyrx definition queries and renderer.

    This class loops through each selected layer in the .lyrx file and checks if every row in the input feature class or layer will be symbolized.
    Note:
        This class does not raise an error if some features do not get symbolized; it only prints a warning.
        This class does not modify the input feature class or layer; it only checks for compatibility with the .lyrx file.
        Unsymbolized features are kept in a copy with a `lyrx_reason` field; its path is logged.

    Raises:
        ValueError: If it discoveres something wrong with chosen layerdefinitions in the .lyrx file.


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
        layer_names: list[str] | None = None,
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
        self.layer_names = layer_names or []
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
        self,
        copied_features_layer: str,
        renderer: dict[str, Any],
        definitionExpression: str | None,
    ) -> bool:
        """Checks that all features in the copied layer matches a CIMUniqueValueClass in renderer."""
        logger.info("Checking renderer:")

        renderer_type = renderer.get("type")
        if renderer_type == "CIMSimpleRenderer":
            logger.info(
                "CIMSimpleRenderer detected which means all features selected by layer will match.\n"
            )
            self._delete_selected(copied_features_layer)
            return True

        if renderer_type != "CIMUniqueValueRenderer":
            logger.warning("Unsupported renderer type: %s", renderer_type)
            logger.warning(
                "Only CIMSimpleRenderer and CIMUniqueValueRenderer are supported by the LyrxCompatibilityChecker class."
            )
            raise ValueError(f"Unsupported renderer type: {renderer_type}")

        if renderer.get("useDefaultSymbol"):
            symbol_layers = (
                renderer.get("defaultSymbol", {})
                .get("symbol", {})
                .get("symbolLayers", [])
            )
            if any(layer.get("enable", False) for layer in symbol_layers):
                logger.info(
                    "Renderer uses default symbol with an enabled layer which means all features selected by layer will match.\n"
                )
                self._delete_selected(copied_features_layer)
                return True

        field_types = {
            f.name.lower(): f.type for f in arcpy.ListFields(copied_features_layer)
        }
        fields: list[str] = renderer.get("fields", [])
        groups = renderer.get("groups", [])

        if not fields or not groups:
            raise ValueError("Renderer is missing fields or groups.\n")

        missing_fields = [field for field in fields if field.lower() not in field_types]
        if missing_fields:
            raise ValueError(
                f"Renderer fields {missing_fields} not found in input. "
                f"Available fields: {sorted(field_types)}"
            )

        renderer_values: set[tuple[str, ...]] = set()

        # iterates through each cim unique value in the renderer and removes matching features from the copied layer
        for group in groups:
            if group.get("type") == "CIMUniqueValueGroup":
                classes = group.get("classes", [])
                if not classes:
                    raise ValueError("Group is missing classes.\n")

                for cls in classes:
                    values = cls.get("values", [])
                    for value in values:
                        if value.get("type") == "CIMUniqueValue":
                            fieldValues: list[str] = value.get("fieldValues", [])

                            if not fieldValues:
                                raise ValueError(
                                    "CIMUniqueValue is missing fieldValues.\n"
                                )

                            if not len(fieldValues) == len(fields):
                                raise ValueError(
                                    "Number of fieldValues does not match number of fields.\n"
                                )

                            renderer_values.add(tuple(fieldValues))
                            sql_expression = " AND ".join(
                                self._build_condition(
                                    field=field,
                                    field_type=field_types[field.lower()],
                                    value=field_value,
                                )
                                for field, field_value in zip(
                                    fields, fieldValues, strict=True
                                )
                            )
                            self._select_definition_query(
                                copied_features_layer, definitionExpression
                            )
                            arcpy.management.SelectLayerByAttribute(
                                copied_features_layer,
                                "SUBSET_SELECTION",
                                sql_expression,
                            )
                            logger.info(
                                "%s features match CIMUniqueValue %s using sql expression: %s",
                                self._count(copied_features_layer),
                                fieldValues,
                                sql_expression,
                            )
                            self._delete_selected(copied_features_layer)

        self._select_definition_query(copied_features_layer, definitionExpression)
        unmatched_count = self._count(copied_features_layer)
        if unmatched_count > 0:
            logger.warning(
                "%s features did not match any renderer class.", unmatched_count
            )
            self._log_unmatched_renderer_values(
                copied_features_layer=copied_features_layer,
                fields=fields,
                renderer_values=renderer_values,
            )
            return False

        logger.info("All features matched at least one renderer class.\n")
        return True

    def check_compatibility(self) -> bool:
        """Makes a copy of input feature class or layer and checks compatibility with selected layers in the .lyrx file by deleting rows that get symbolized from copy feature class or layer. Prints the result of the compatibility check."""
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

        definition_query_oids: dict[str, set[int]] = {}
        definition_expressions: list[str] = []

        for layer in self.selected_layers:
            layer_name: str = layer.get("name", "")
            logger.info("Checking compatibility for layer: %s", layer_name)
            definitionExpression: str | None = layer.get("featureTable", {}).get(
                "definitionExpression"
            )
            renderer = layer.get("renderer", {})

            if definitionExpression:
                definition_expressions.append(definitionExpression)
                logger.info("Definition query: %s", definitionExpression)

            try:
                self._select_definition_query(
                    copied_features_layer, definitionExpression
                )
            except Exception as e:
                logger.warning(
                    "Error selecting definition query for layer %s: %s", layer_name, e
                )
                continue

            matched_count = self._count(copied_features_layer)
            if matched_count == 0:
                logger.warning(
                    "No features match the definition query for layer: %s\n",
                    layer_name,
                )
                continue

            logger.info(
                "%s Total features match the definition query for layer: %s",
                matched_count,
                layer_name,
            )
            definition_query_oids[layer_name] = self._selected_oids(
                copied_features_layer
            )
            try:
                self.check_renderer(
                    copied_features_layer, renderer, definitionExpression
                )
            except Exception as e:
                logger.warning(
                    "Error checking renderer for layer %s: %s", layer_name, e
                )

        arcpy.management.SelectLayerByAttribute(
            copied_features_layer, "CLEAR_SELECTION"
        )
        remaining_count = self._count(copied_features_layer)
        arcpy.management.Delete(copied_features_layer)

        if remaining_count == 0:
            self.wfm.delete_created_files(delete_targets=[copied_features])
            logger.info("All features are symbolized by the selected layers.\n")
            return True

        reason_counts = self._write_unmatched_reasons(
            copied_features=copied_features,
            definition_query_oids=definition_query_oids,
        )
        logger.warning(
            "%s features will not be symbolized. Breakdown by reason:",
            remaining_count,
        )
        for reason, count in reason_counts.most_common():
            logger.warning("  %s: %s", reason, count)

        if reason_counts[NO_DEFINITION_QUERY_MATCH]:
            self._log_definition_query_field_values(
                copied_features=copied_features,
                definition_expressions=definition_expressions,
            )

        # Untrack so a later wfm.delete_created_files() keeps it for inspection.
        self.wfm.created_paths.discard(str(copied_features))
        logger.warning(
            "Unsymbolized features kept for inspection (see field '%s'): %s\n",
            REASON_FIELD,
            copied_features,
        )
        return False

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

    def _build_condition(self, field: str, field_type: str, value: str) -> str:
        if value == NULL_VALUE:
            return f"{field} IS NULL"
        converted = self.convert_field_value(field_type, value)
        if isinstance(converted, str):
            escaped = converted.replace("'", "''")
            return f"{field} = '{escaped}'"
        return f"{field} = {converted}"

    @staticmethod
    def _normalize_value(value: object) -> str:
        """Formats a data value the way .lyrx fieldValues store it."""
        if value is None:
            return NULL_VALUE
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    @staticmethod
    def _count(layer: str) -> int:
        return int(arcpy.management.GetCount(layer)[0])

    @staticmethod
    def _select_definition_query(layer: str, definition_expression: str | None) -> None:
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=layer,
            selection_type="NEW_SELECTION",
            where_clause=definition_expression or "1=1",
        )

    def _delete_selected(self, layer: str) -> None:
        if self._count(layer) > 0:
            arcpy.management.DeleteFeatures(layer)

    @staticmethod
    def _selected_oids(layer: str) -> set[int]:
        oids: set[int] = set()
        with arcpy.da.SearchCursor(layer, ["OID@"]) as cursor:
            for row in cursor:
                oids.add(row[0])
        return oids

    def _count_combinations(
        self, dataset: str, fields: list[str], where_clause: str | None = None
    ) -> Counter[tuple[str, ...]]:
        combinations: Counter[tuple[str, ...]] = Counter()
        with arcpy.da.SearchCursor(dataset, fields, where_clause) as cursor:
            for row in cursor:
                combinations[tuple(self._normalize_value(v) for v in row)] += 1
        return combinations

    def _log_unmatched_renderer_values(
        self,
        copied_features_layer: str,
        fields: list[str],
        renderer_values: set[tuple[str, ...]],
    ) -> None:
        combinations = self._count_combinations(copied_features_layer, fields)
        logger.warning(
            "Unmatched value combinations for renderer fields %s (top %s of %s):",
            fields,
            TOP_N_COMBINATIONS,
            len(combinations),
        )
        for combination, count in combinations.most_common(TOP_N_COMBINATIONS):
            if combination in renderer_values:
                logger.warning(
                    "  %s: %s features - exists in renderer, so the SQL selection failed",
                    combination,
                    count,
                )
            else:
                logger.warning(
                    "  %s: %s features - missing from renderer", combination, count
                )
        logger.info("\n")

    def _write_unmatched_reasons(
        self, copied_features: str, definition_query_oids: dict[str, set[int]]
    ) -> Counter[str]:
        arcpy.management.AddField(
            in_table=copied_features,
            field_name=REASON_FIELD,
            field_type="TEXT",
            field_length=REASON_FIELD_LENGTH,
        )
        reason_counts: Counter[str] = Counter()
        with arcpy.da.UpdateCursor(copied_features, ["OID@", REASON_FIELD]) as cursor:
            for oid, _ in cursor:
                layers = [
                    name for name, oids in definition_query_oids.items() if oid in oids
                ]
                reason = (
                    f"{NO_RENDERER_CLASS}:{','.join(layers)}"[:REASON_FIELD_LENGTH]
                    if layers
                    else NO_DEFINITION_QUERY_MATCH
                )
                cursor.updateRow([oid, reason])
                reason_counts[reason] += 1
        return reason_counts

    def _log_definition_query_field_values(
        self, copied_features: str, definition_expressions: list[str]
    ) -> None:
        field_names = {
            f.name.lower(): f.name
            for f in arcpy.ListFields(copied_features)
            if f.type not in ("OID", "Geometry") and f.name != REASON_FIELD
        }
        referenced_fields: list[str] = []
        for expression in definition_expressions:
            for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expression):
                name = field_names.get(token.lower())
                if name and name not in referenced_fields:
                    referenced_fields.append(name)

        if not referenced_fields:
            logger.warning("Definition queries reference no fields in the input.")
            return

        combinations = self._count_combinations(
            dataset=copied_features,
            fields=referenced_fields,
            where_clause=f"{REASON_FIELD} = '{NO_DEFINITION_QUERY_MATCH}'",
        )
        logger.warning(
            "%s value combinations for definition query fields %s (top %s of %s):",
            NO_DEFINITION_QUERY_MATCH,
            referenced_fields,
            TOP_N_COMBINATIONS,
            len(combinations),
        )
        for combination, count in combinations.most_common(TOP_N_COMBINATIONS):
            logger.warning("  %s: %s features", combination, count)


if __name__ == "__main__":
    LyrxCompatibilityChecker(
        lyrx_file="",
        feature_class_or_layer="",
        wfm=WorkFileManager(config=core_config.WorkFileConfig(root_file="")),
        dataset="",
    ).check_compatibility()
