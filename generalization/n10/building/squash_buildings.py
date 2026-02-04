import arcpy
import csv

import config
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy
from env_setup import environment_setup
from file_manager.n10.file_manager_buildings import Building_N10


# OBS: HENTER FRA TEMP


class SquashBuildings:
    """
    Class to squash adjacent buildings with building types from the same category into a
    single building.
    """

    def __init__(self):
        """
        Creates an instance of SquashBuildings.
        """
        environment_setup.main()
        self.building_path = config.default_project_workspace + "\\bygning_omrade"
        self.other_building_path = (
            config.default_project_workspace + "\\fkb_bygning_omrade"
        )

    @timing_decorator
    def harmonize_attributes(self, dissolved_fc, original_fc):
        """Assign common values from original feature class to dissolved feature class."""
        fields = {
            f.name: f.type
            for f in arcpy.ListFields(original_fc)
            if f.type not in ("OID", "Geometry")
            and f.name not in ("SHAPE_Area", "SHAPE_Length")
        }

        arcpy.analysis.SpatialJoin(
            target_features=dissolved_fc,
            join_features=original_fc,
            out_feature_class=Building_N10.squash_buildings___harmonize_attributes___n10.value,
            join_operation="JOIN_ONE_TO_MANY",
            match_option="INTERSECT",
        )

        lookup = {}
        with arcpy.da.SearchCursor(
            Building_N10.squash_buildings___harmonize_attributes___n10.value,
            ["TARGET_FID"] + list(fields.keys()),
        ) as sc:
            for row in sc:
                g = row[0]
                if g not in lookup:
                    lookup[g] = {fld: set() for fld in fields}
                for fld, val in zip(fields, row[1:]):
                    lookup[g][fld].add(val)

        variants = {
            "String": "TEXT",
            "Integer": "LONG",
            "SmallInteger": "LONG",
            "Double": "DOUBLE",
            "Date": "DATE",
        }

        for name, type in fields.items():
            if name not in [
                f.name
                for f in arcpy.ListFields(dissolved_fc)
                if not f.name.endswith("_1")
            ]:
                field_type = variants[type]
                arcpy.management.AddField(dissolved_fc, name, field_type)

        with arcpy.da.UpdateCursor(dissolved_fc, ["OID@"] + list(fields.keys())) as uc:
            for row in uc:
                g = row[0]
                if g not in lookup:
                    continue

                new_vals = []
                for fld in fields:
                    vals = lookup[g][fld]
                    if len(vals) == 1:
                        new_vals.append(next(iter(vals)))
                    else:
                        new_vals.append(None)

                if "bygningsnummer" in fields:
                    idx = list(fields.keys()).index("bygningsnummer")
                    new_vals[idx] = -9999

                uc.updateRow([g] + new_vals)

    @timing_decorator
    def find_buildings_to_squash(self):
        """
        Find adjacent buildings that share building type category.
        """
        expected_cols = ["Drivhus", "Skole", "Sykehus", "Næringsbygg", "Fastboende"]

        allowed = {col: set() for col in expected_cols}

        with open(config.building_csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")

            actual = {}
            for c in reader.fieldnames:
                clean = c.replace("\ufeff", "").strip()
                actual[clean] = c

            colmap = {}
            for col in expected_cols:
                if col not in actual:
                    raise KeyError(
                        f"Column '{col}' not found in CSV. Found: {list(actual.keys())}"
                    )
                colmap[col] = actual[col]

            for row in reader:
                for logical, real in colmap.items():
                    val = row[real]
                    if val and val.strip():
                        allowed[logical].add(val.strip())

        sql_parts = []

        for col, values in allowed.items():
            if values:
                in_list = ",".join(f"'{v}'" for v in values)
                sql_parts.append(
                    f"(bygningstype_1 IN ({in_list}) AND bygningstype IN ({in_list}))"
                )

        sql = (
            "(" + " OR ".join(sql_parts) + ") "
            "AND bygningsnummer <> bygningsnummer_1 "
            "AND bygningstype IS NOT NULL"
        )

        return sql

    @timing_decorator
    def get_buildings(self):
        """
        Run the squash building process by joining buildings and dissolving common lines.
        """
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.other_building_path,
            expression="objtype = 'AnnenBygning'",
            output_name=Building_N10.squash_buildings___other_buildings___n10.value,
        )

        arcpy.analysis.SpatialJoin(
            target_features=self.building_path,
            join_features=self.building_path,
            out_feature_class=Building_N10.squash_buildings___adjacent_buildings___n10.value,
            join_operation="JOIN_ONE_TO_MANY",
            join_type="KEEP_COMMON",
            match_option="INTERSECT",
        )

        sql = self.find_buildings_to_squash()

        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=Building_N10.squash_buildings___adjacent_buildings___n10.value,
            expression=sql,
            output_name=Building_N10.squash_buildings___neighbors___n10.value,
            selection_type="NEW_SELECTION",
        )

        arcpy.management.Dissolve(
            in_features=Building_N10.squash_buildings___neighbors___n10.value,
            out_feature_class=Building_N10.squash_buildings___neighbors_dissolved___n10.value,
            multi_part="MULTI_PART",
        )

        arcpy.management.MultipartToSinglepart(
            in_features=Building_N10.squash_buildings___neighbors_dissolved___n10.value,
            out_feature_class=Building_N10.squash_buildings___clustered___n10.value,
        )

        self.harmonize_attributes(
            dissolved_fc=Building_N10.squash_buildings___clustered___n10.value,
            original_fc=self.building_path,
        )

        arcpy.analysis.Erase(
            in_features=self.building_path,
            erase_features=Building_N10.squash_buildings___clustered___n10.value,
            out_feature_class=Building_N10.squash_buildings___non_clustered___n10.value,
        )

        arcpy.management.Merge(
            inputs=[
                Building_N10.squash_buildings___clustered___n10.value,
                Building_N10.squash_buildings___non_clustered___n10.value,
            ],
            output=Building_N10.squash_buildings___final___n10.value,
        )

        arcpy.management.DeleteField(
            Building_N10.squash_buildings___final___n10.value, ["ORIG_FID"]
        )

        arcpy.management.Append(
            inputs=Building_N10.squash_buildings___other_buildings___n10.value,
            target=Building_N10.squash_buildings___final___n10.value,
            schema_type="NO_TEST",
        )


if __name__ == "__main__":
    squash = SquashBuildings()
    squash.get_buildings()
