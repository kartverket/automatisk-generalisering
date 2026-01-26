import arcpy

import config
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy
from env_setup import environment_setup
from file_manager.n10.file_manager_buildings import Building_N10


# OBS: HENTER FRA TEMP


class SquashBuildings:
    """
    Class to squash adjacent building with the same value for bygningstype into a
    single building.
    """

    def __init__(self):
        """
        Creates an instance of SquashBuildings.
        """
        environment_setup.main()
        self.building_path = config.default_project_workspace + "\\bygning_omrade"

    @timing_decorator
    def harmonize_attributes(self, dissolved_fc, original_fc, group_field):
        """Assign common values from original feature class to dissolved feature class."""
        fields = {
            f.name: f.type
            for f in arcpy.ListFields(original_fc)
            if f.type not in ("OID", "Geometry")
            and f.name != group_field
            and f.name not in ("SHAPE_Area", "SHAPE_Length")
        }

        lookup = {}
        with arcpy.da.SearchCursor(
            original_fc, [group_field] + list(fields.keys())
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
                if not f.name.endswith("_1") or f.name == "ORIG_FID"
            ]:
                field_type = variants[type]
                arcpy.management.AddField(dissolved_fc, name, field_type)

        with arcpy.da.UpdateCursor(
            dissolved_fc, [group_field] + list(fields.keys())
        ) as uc:
            for row in uc:
                g = row[0]
                new_vals = []
                for fld in fields:
                    vals = lookup[g][fld]
                    new_vals.append(next(iter(vals)) if len(vals) == 1 else None)

                if "bygningsnummer" in fields:
                    idx = list(fields.keys()).index("bygningsnummer")
                    new_vals[idx] = -9999

                uc.updateRow([g] + new_vals)

    @timing_decorator
    def get_buildings(self):
        """
        Run the squash building process by joining buildings and dissolving common lines.
        """
        arcpy.analysis.SpatialJoin(
            target_features=self.building_path,
            join_features=self.building_path,
            out_feature_class=Building_N10.squash_buildings___adjacent_buildings___n10.value,
            join_operation="JOIN_ONE_TO_MANY",
            join_type="KEEP_COMMON",
            match_option="INTERSECT",
        )

        sql = (
            "bygningstype = bygningstype_1 "
            "AND bygningsnummer <> bygningsnummer_1 "
            "AND bygningstype IS NOT NULL"
        )

        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=Building_N10.squash_buildings___adjacent_buildings___n10.value,
            expression=sql,
            output_name=Building_N10.squash_buildings___neighbors___n10.value,
            selection_type="NEW_SELECTION",
        )

        arcpy.management.Dissolve(
            in_features=Building_N10.squash_buildings___neighbors___n10.value,
            out_feature_class=Building_N10.squash_buildings___neighbors_dissolved___n10.value,
            dissolve_field=["bygningstype"],
            multi_part="MULTI_PART",
        )

        arcpy.management.MultipartToSinglepart(
            in_features=Building_N10.squash_buildings___neighbors_dissolved___n10.value,
            out_feature_class=Building_N10.squash_buildings___clustered___n10.value,
        )

        self.harmonize_attributes(
            dissolved_fc=Building_N10.squash_buildings___clustered___n10.value,
            original_fc=self.building_path,
            group_field="bygningstype",
        )

        custom_arcpy.select_location_and_make_permanent_feature(
            input_layer=self.building_path,
            overlap_type="INTERSECT",
            select_features=Building_N10.squash_buildings___clustered___n10.value,
            output_name=Building_N10.squash_buildings___non_clustered___n10.value,
            selection_type="NEW_SELECTION",
            inverted=True,
        )

        arcpy.management.Merge(
            inputs=[
                Building_N10.squash_buildings___clustered___n10.value,
                Building_N10.squash_buildings___non_clustered___n10.value,
            ],
            output=Building_N10.squash_buildings___final___n10.value,
        )


if __name__ == "__main__":
    squash = SquashBuildings()
    squash.get_buildings()
