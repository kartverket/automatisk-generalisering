import arcpy

from composition_configs import core_config, logic_config
import config
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy
from env_setup import environment_setup
from file_manager.n10.file_manager_roads import Road_N10
from file_manager.work_file_manager import WorkFileManager


class CleanTrails:
    """
    Class to remove parallell trails.
    """

    def __init__(self, clean_trails_config):
        """
        Creates an instance of CleanTrails.
        """
        environment_setup.main()
        self.trails_path = config.default_project_workspace + "\\veglenke"
        self.work_file_manager = WorkFileManager(
            config=clean_trails_config.work_file_manager_config
        )

    @timing_decorator
    def clean_trails(self):
        """
        Cleans and simplifies the trail network by pruning parallell running trails and
        removing dangles.
        """
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.trails_path,
            expression="objtype IN ('Barmarksløype')",
            output_name=Road_N10.data_selection___barmarksloype___n10_road.value,
        )

        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.trails_path,
            expression="objtype IN ('Sti')",
            output_name=Road_N10.data_selection___sti___n10_road.value,
        )

        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.trails_path,
            expression="objtype IN ('Traktorveg')",
            output_name=Road_N10.data_selection___traktorveg___n10_road.value,
        )

        arcpy.management.Merge(
            inputs=[
                Road_N10.data_selection___barmarksloype___n10_road.value,
                Road_N10.data_selection___sti___n10_road.value,
                Road_N10.data_selection___traktorveg___n10_road.value,
            ],
            output=Road_N10.data_selection___trails___n10_road.value,
        )

        arcpy.analysis.Erase(
            in_features=self.trails_path,
            erase_features=Road_N10.data_selection___trails___n10_road.value,
            out_feature_class=Road_N10.data_selection___not_trails___n10_road.value,
        )

        arcpy.analysis.Buffer(
            in_features=Road_N10.data_selection___barmarksloype___n10_road.value,
            out_feature_class=Road_N10.data_selection___barmarksloype_buffered___n10_road.value,
            buffer_distance_or_field="10 Meters",
            line_end_type="FLAT",
            dissolve_option="NONE",
        )

        arcpy.analysis.Buffer(
            in_features=Road_N10.data_selection___sti___n10_road.value,
            out_feature_class=Road_N10.data_selection___sti_buffered___n10_road.value,
            buffer_distance_or_field="10 Meters",
            line_end_type="FLAT",
            dissolve_option="NONE",
        )

        arcpy.analysis.Buffer(
            in_features=Road_N10.data_selection___traktorveg___n10_road.value,
            out_feature_class=Road_N10.data_selection___traktorveg_buffered___n10_road.value,
            buffer_distance_or_field="10 Meters",
            line_end_type="FLAT",
            dissolve_option="NONE",
        )

        arcpy.management.Dissolve(
            Road_N10.data_selection___barmarksloype_buffered___n10_road.value,
            out_feature_class=Road_N10.data_selection___barmarksloype_buffered_dissolved___n10_road.value,
            dissolve_field=["objtype"],
            multi_part="SINGLE_PART",
        )

        arcpy.management.Dissolve(
            Road_N10.data_selection___sti_buffered___n10_road.value,
            out_feature_class=Road_N10.data_selection___sti_buffered_dissolved___n10_road.value,
            dissolve_field=["objtype"],
            multi_part="SINGLE_PART",
        )

        arcpy.management.Dissolve(
            Road_N10.data_selection___traktorveg_buffered___n10_road.value,
            out_feature_class=Road_N10.data_selection___traktorveg_buffered_dissolved___n10_road.value,
            dissolve_field=["objtype"],
            multi_part="SINGLE_PART",
        )

        arcpy.management.Merge(
            inputs=[
                Road_N10.data_selection___barmarksloype_buffered_dissolved___n10_road.value,
                Road_N10.data_selection___sti_buffered_dissolved___n10_road.value,
                Road_N10.data_selection___traktorveg_buffered_dissolved___n10_road.value,
            ],
            output=Road_N10.data_selection___trails_buffered___n10_road.value,
        )

        arcpy.analysis.CountOverlappingFeatures(
            in_features=Road_N10.data_selection___trails_buffered___n10_road.value,
            out_feature_class=Road_N10.data_selection___parallell_trails_overlaps___n10_road.value,
            min_overlap_count=2,
        )

        arcpy.management.MultipartToSinglepart(
            in_features=Road_N10.data_selection___parallell_trails_overlaps___n10_road.value,
            out_feature_class=Road_N10.data_selection___parallell_trails_overlaps_singlepart___n10_road.value,
        )

        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=Road_N10.data_selection___parallell_trails_overlaps_singlepart___n10_road.value,
            expression="Shape_Area >= 1000",
            output_name=Road_N10.data_selection___large_overlap_trail_pairs___n10_road.value,
        )

        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=Road_N10.data_selection___large_overlap_trail_pairs___n10_road.value,
            expression="Shape_Length >= 100",
            output_name=Road_N10.data_selection___long_overlaps___n10_road.value,
        )

        arcpy.analysis.Intersect(
            in_features=[
                Road_N10.data_selection___long_overlaps___n10_road.value,
                Road_N10.data_selection___trails___n10_road.value,
            ],
            out_feature_class=Road_N10.data_selection___trails_with_overlap___n10_road.value,
            join_attributes="ALL",
            output_type="LINE",
        )

        arcpy.management.Dissolve(
            in_features=Road_N10.data_selection___trails_with_overlap___n10_road.value,
            out_feature_class=Road_N10.data_selection___trails_with_overlap_dissolved___n10_road.value,
            dissolve_field=["objtype"],
            multi_part="SINGLE_PART",
        )

        arcpy.management.AddField(
            Road_N10.data_selection___trails_with_overlap_dissolved___n10_road.value,
            "hierarchy",
            "SHORT",
        )

        arcpy.management.CalculateField(
            in_table=Road_N10.data_selection___trails_with_overlap_dissolved___n10_road.value,
            field="hierarchy",
            expression="mapping[!objtype!]",
            expression_type="PYTHON3",
            code_block="""mapping = {
            'Barmarksløype': 0,
            'Sti': 1,
            'GangSykkelveg': 2,
            'Traktorveg': 3
        }
        """,
        )

        arcpy.edit.Densify(
            in_features=Road_N10.data_selection___trails_with_overlap_dissolved___n10_road.value,
            densification_method="DISTANCE",
            distance="5 Meters",
        )

        arcpy.management.FeatureVerticesToPoints(
            in_features=Road_N10.data_selection___trails_with_overlap_dissolved___n10_road.value,
            out_feature_class=Road_N10.data_selection___trail_points___n10_road.value,
        )

        arcpy.management.JoinField(
            in_data=Road_N10.data_selection___trail_points___n10_road.value,
            in_field="ORIG_FID",
            join_table=Road_N10.data_selection___trails_with_overlap_dissolved___n10_road.value,
            join_field="OBJECTID",
            fields=["objtype"],
        )

        arcpy.analysis.GenerateNearTable(
            in_features=Road_N10.data_selection___trail_points___n10_road.value,
            near_features=Road_N10.data_selection___trail_points___n10_road.value,
            out_table=Road_N10.data_selection___trail_points_near_table___n10_road.value,
            search_radius="5 Meters",
            closest="ALL",
            method="PLANAR",
        )

        arcpy.management.JoinField(
            in_data=Road_N10.data_selection___trail_points_near_table___n10_road.value,
            in_field="IN_FID",
            join_table=Road_N10.data_selection___trail_points___n10_road.value,
            join_field="OBJECTID",
            fields=["ORIG_FID"],
        )
        arcpy.management.AlterField(
            Road_N10.data_selection___trail_points_near_table___n10_road.value,
            "ORIG_FID",
            new_field_name="IN_trail_id",
        )

        arcpy.management.JoinField(
            in_data=Road_N10.data_selection___trail_points_near_table___n10_road.value,
            in_field="NEAR_FID",
            join_table=Road_N10.data_selection___trail_points___n10_road.value,
            join_field="OBJECTID",
            fields=["ORIG_FID"],
        )
        arcpy.management.AlterField(
            Road_N10.data_selection___trail_points_near_table___n10_road.value,
            "ORIG_FID",
            new_field_name="NEAR_trail_id",
        )

        arcpy.management.JoinField(
            in_data=Road_N10.data_selection___trail_points_near_table___n10_road.value,
            in_field="IN_FID",
            join_table=Road_N10.data_selection___trail_points___n10_road.value,
            join_field="OBJECTID",
            fields=["objtype_1"],
        )
        arcpy.management.AlterField(
            Road_N10.data_selection___trail_points_near_table___n10_road.value,
            "objtype_1",
            new_field_name="IN_objtype",
        )

        arcpy.management.JoinField(
            in_data=Road_N10.data_selection___trail_points_near_table___n10_road.value,
            in_field="NEAR_FID",
            join_table=Road_N10.data_selection___trail_points___n10_road.value,
            join_field="OBJECTID",
            fields=["objtype_1"],
        )
        arcpy.management.AlterField(
            Road_N10.data_selection___trail_points_near_table___n10_road.value,
            "objtype_1",
            new_field_name="NEAR_objtype",
        )

        arcpy.management.MakeTableView(
            Road_N10.data_selection___trail_points_near_table___n10_road.value,
            "near_view",
            "IN_trail_id <> NEAR_trail_id AND IN_objtype <> NEAR_objtype",
        )

        arcpy.analysis.Statistics(
            in_table="near_view",
            out_table=Road_N10.data_selection___near_table_stats___n10_road.value,
            statistics_fields=[["NEAR_DIST", "COUNT"]],
            case_field=["IN_trail_id", "NEAR_trail_id"],
        )

        parallel_pairs = {}

        with arcpy.da.SearchCursor(
            Road_N10.data_selection___near_table_stats___n10_road.value,
            ["IN_trail_id", "NEAR_trail_id", "COUNT_NEAR_DIST"],
        ) as cur:
            for a, b, count in cur:
                if count >= 10:
                    parallel_pairs.setdefault(a, set()).add(b)
                    parallel_pairs.setdefault(b, set()).add(a)

        remove_ids = set()

        with arcpy.da.SearchCursor(
            Road_N10.data_selection___trails_with_overlap_dissolved___n10_road.value,
            ["OBJECTID", "hierarchy"],
        ) as cur:
            hierarchy = {oid: h for oid, h in cur}

        for a, neighbors in parallel_pairs.items():
            for b in neighbors:
                if hierarchy[a] > hierarchy[b]:
                    remove_ids.add(a)
                elif hierarchy[a] < hierarchy[b]:
                    remove_ids.add(b)
                else:
                    continue

        arcpy.analysis.Select(
            in_features=Road_N10.data_selection___trails_with_overlap_dissolved___n10_road.value,
            out_feature_class=Road_N10.data_selection___trails_in_overlap_to_remove___n10_road.value,
            where_clause=f"OBJECTID IN ({','.join(map(str, remove_ids))})",
        )

        arcpy.analysis.Select(
            in_features=Road_N10.data_selection___trails_with_overlap_dissolved___n10_road.value,
            out_feature_class=Road_N10.data_selection___trails_in_overlap_to_keep___n10_road.value,
            where_clause=f"OBJECTID NOT IN ({','.join(map(str, remove_ids))})",
        )

        arcpy.analysis.Erase(
            in_features=Road_N10.data_selection___trails_in_overlap_to_remove___n10_road.value,
            erase_features=Road_N10.data_selection___trails_in_overlap_to_keep___n10_road.value,
            out_feature_class=Road_N10.data_selection___trails_to_remove___n10_road.value,
        )

        arcpy.analysis.Erase(
            in_features=Road_N10.data_selection___trails_to_remove___n10_road.value,
            erase_features=Road_N10.data_selection___large_overlap_trail_pairs___n10_road.value,
            out_feature_class=Road_N10.data_selection___dangles_not_covered___n10_road.value,
        )

        arcpy.management.MultipartToSinglepart(
            in_features=Road_N10.data_selection___dangles_not_covered___n10_road.value,
            out_feature_class=Road_N10.data_selection___dangles_not_covered_singlepart___n10_road.value,
        )

        custom_arcpy.select_attribute_and_make_feature_layer(
            input_layer=Road_N10.data_selection___dangles_not_covered_singlepart___n10_road.value,
            expression="Shape_Length >= 70",
            output_name=Road_N10.data_selection___long_dangles_not_covered___n10_road.value,
        )

        arcpy.analysis.Erase(
            in_features=Road_N10.data_selection___trails_to_remove___n10_road.value,
            erase_features=Road_N10.data_selection___long_dangles_not_covered___n10_road.value,
            out_feature_class=Road_N10.data_selection___trails_to_remove_without_dangles___n10_road.value,
        )

        arcpy.analysis.Erase(
            in_features=Road_N10.data_selection___trails___n10_road.value,
            erase_features=Road_N10.data_selection___trails_to_remove_without_dangles___n10_road.value,
            out_feature_class=Road_N10.data_selection___trails_to_keep___n10_road.value,
        )

        arcpy.management.MultipartToSinglepart(
            in_features=Road_N10.data_selection___trails_to_keep___n10_road.value,
            out_feature_class=Road_N10.data_selection___trails_to_keep_singlepart___n10_road.value,
        )

        arcpy.analysis.SpatialJoin(
            target_features=Road_N10.data_selection___trails_to_keep_singlepart___n10_road.value,
            join_features=Road_N10.data_selection___trails_to_remove___n10_road.value,
            out_feature_class=Road_N10.data_selection___dangles_not_wanted___n10_road.value,
            join_operation="JOIN_ONE_TO_ONE",
            join_type="KEEP_ALL",
            match_option="INTERSECT",
        )

        custom_arcpy.select_attribute_and_make_feature_layer(
            input_layer=Road_N10.data_selection___dangles_not_wanted___n10_road.value,
            expression="Join_Count = 2 AND Shape_Length < 50 OR Join_Count = 1 AND Shape_Length < 20",
            output_name=Road_N10.data_selection___dangles_to_remove___n10_road.value,
        )

        arcpy.analysis.Erase(
            in_features=Road_N10.data_selection___trails_to_keep___n10_road.value,
            erase_features=Road_N10.data_selection___dangles_to_remove___n10_road.value,
            out_feature_class=Road_N10.data_selection___trails_final___n10_road.value,
        )

        arcpy.management.Merge(
            inputs=[
                Road_N10.data_selection___trails_final___n10_road.value,
                Road_N10.data_selection___not_trails___n10_road.value,
            ],
            output=Road_N10.data_selection___roads_final___n10_road.value,
        )

        self.work_file_manager.delete_created_files()


@timing_decorator
def run():
    """
    Run the trail cleaning process.
    """
    root = Road_N10.data_selection___trails_root___n10_road.value

    config = logic_config.CleanTrailsKwargs(
        work_file_manager_config=core_config.WorkFileConfig(root),
        maximum_length=500,
        root_file=root,
        sql_expressions=None,
    )

    clean_trails = CleanTrails(config)
    clean_trails.clean_trails()


if __name__ == "__main__":
    run()
