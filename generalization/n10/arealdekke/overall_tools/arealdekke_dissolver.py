from collections import defaultdict

import arcpy

from composition_configs import core_config, logic_config
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools.geometry_tools import GeometryValidator
from custom_tools.general_tools.partition_iterator import PartitionIterator
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from input_data import input_n10


class ArealdekkeDissolver:
    """
    General dissolver for arealdekke.
    Currently dissolves samferdsel, snaumark and not_snau seperately and merges them back together at the end.
    Rules:
        -   Snaumark is dissolved based on dgfcd_feature_alpha
        -   not_snau is dissolved based on arealdekke,
        -   samferdsel is dissolved based on arealdekke and index(fishnet) to avoid large polygons
        -   gang og sykkelvei is to be preserved for a more complicated dissolve in another class.
    """

    def __init__(
        self, areal_dekke_dissolver_config: logic_config.ArealDekkeDissolverInitKwargs
    ):
        self.input_arealdekke = areal_dekke_dissolver_config.input_feature
        self.output_feature = areal_dekke_dissolver_config.output_feature

        self.index_col = areal_dekke_dissolver_config.index_column_name

        self.geometry_validator = GeometryValidator()

        self.wfm = WorkFileManager(
            config=areal_dekke_dissolver_config.work_file_manager_config
        )

        self.files = self.create_wfm_gdbs(self.wfm)

    def create_wfm_gdbs(self, wfm: WorkFileManager) -> dict:
        arealdekke_input = wfm.build_file_path(
            file_name="arealdekke_input", file_type="gdb"
        )
        arealdekke_snaumark = wfm.build_file_path(
            file_name="arealdekke_snaumark", file_type="gdb"
        )
        arealdekke_snaumark_dissolved = wfm.build_file_path(
            file_name="arealdekke_snaumark_dissolved", file_type="gdb"
        )
        arealdekke_not_snau = wfm.build_file_path(
            file_name="arealdekke_not_snau", file_type="gdb"
        )
        arealdekke_not_snau_dissolved = wfm.build_file_path(
            file_name="arealdekke_not_snau_dissolved", file_type="gdb"
        )
        arealdekke_samferdsel = wfm.build_file_path(
            file_name="arealdekke_samferdsel", file_type="gdb"
        )
        arealdekke_samferdsel_dissolved = wfm.build_file_path(
            file_name="arealdekke_samferdsel_dissolved", file_type="gdb"
        )
        arealdekke_dissolved_Norge = wfm.build_file_path(
            file_name="arealdekke_dissolved_Norge", file_type="gdb"
        )
        arealdekke_identity = wfm.build_file_path(
            file_name="arealdekke_identity", file_type="gdb"
        )
        arealdekke_gangogsykkel = wfm.build_file_path(
            file_name="arealdekke_gangogsykkel", file_type="gdb"
        )

        return {
            "arealdekke_input": arealdekke_input,
            "arealdekke_snaumark": arealdekke_snaumark,
            "arealdekke_snaumark_dissolved": arealdekke_snaumark_dissolved,
            "arealdekke_not_snau": arealdekke_not_snau,
            "arealdekke_not_snau_dissolved": arealdekke_not_snau_dissolved,
            "arealdekke_dissolved_Norge": arealdekke_dissolved_Norge,
            "arealdekke_samferdsel": arealdekke_samferdsel,
            "arealdekke_samferdsel_dissolved": arealdekke_samferdsel_dissolved,
            "arealdekke_identity": arealdekke_identity,
            "arealdekke_gangogsykkel": arealdekke_gangogsykkel,
        }

    @timing_decorator
    def fetch_divide_data(self) -> None:
        """
        This function fetches the data and divides it based on the rules described in the class docstring.
        It also preserves gang og sykkelvei for a more complicated dissolve in another class.
        """
        arcpy.management.CopyFeatures(
            in_features=self.input_arealdekke,
            out_feature_class=self.files["arealdekke_input"],
        )

        snaumark = "snaumark"
        not_snau = "not_snau"
        samferdsel = "samferdsel"
        arcpy.management.MakeFeatureLayer(
            in_features=self.files["arealdekke_input"],
            out_layer=snaumark,
            where_clause="arealdekke IN ('Snaumark_frisk', 'Snaumark_impediment', 'Snaumark_konstruert', 'Snaumark_middels_frisk', 'Snaumark_skrinn', 'Snaumark_uspesifisert')",
        )
        arcpy.management.MakeFeatureLayer(
            in_features=self.files["arealdekke_input"],
            out_layer=not_snau,
            where_clause="arealdekke NOT IN ('Snaumark_frisk', 'Snaumark_impediment', 'Snaumark_konstruert', 'Snaumark_middels_frisk', 'Snaumark_skrinn', 'Snaumark_uspesifisert', 'Samferdsel')",
        )
        arcpy.management.MakeFeatureLayer(
            in_features=self.files["arealdekke_input"],
            out_layer=samferdsel,
            where_clause="arealdekke IN ('Samferdsel')",
        )

        # to preserve gang og sykkelvei we remove them and we merge it back at the end,
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=samferdsel,
            selection_type="NEW_SELECTION",
            where_clause="arealbruk_underklasse = 'GangSykkelVeg'",
        )
        arcpy.management.CopyFeatures(
            in_features=samferdsel,
            out_feature_class=self.files["arealdekke_gangogsykkel"],
        )
        arcpy.management.DeleteFeatures(in_features=samferdsel)
        arcpy.management.CopyFeatures(
            in_features=snaumark, out_feature_class=self.files["arealdekke_snaumark"]
        )
        arcpy.management.CopyFeatures(
            in_features=not_snau, out_feature_class=self.files["arealdekke_not_snau"]
        )
        arcpy.management.CopyFeatures(
            in_features=samferdsel,
            out_feature_class=self.files["arealdekke_samferdsel"],
        )

    @timing_decorator
    def dissolve(self) -> None:
        """
        Dissolves the data based on the rules described in the class docstring.
        """
        not_snau_dis_mem = "in_memory\\not_snau_dis_mem"
        arcpy.management.Dissolve(
            in_features=self.files["arealdekke_not_snau"],
            out_feature_class=not_snau_dis_mem,
            dissolve_field=["arealdekke", self.index_col],
            multi_part="SINGLE_PART",
        )
        arcpy.management.Dissolve(
            in_features=not_snau_dis_mem,
            out_feature_class=self.files["arealdekke_not_snau_dissolved"],
            dissolve_field=["arealdekke"],
            multi_part="SINGLE_PART",
        )

        snau_dis_mem = "in_memory\\snau_dis_mem"
        arcpy.management.Dissolve(
            in_features=self.files["arealdekke_snaumark"],
            out_feature_class=snau_dis_mem,
            dissolve_field=["dgfcd_feature_alpha", self.index_col],
            multi_part="SINGLE_PART",
        )
        arcpy.management.Dissolve(
            in_features=snau_dis_mem,
            out_feature_class=self.files["arealdekke_snaumark_dissolved"],
            dissolve_field=["dgfcd_feature_alpha"],
            multi_part="SINGLE_PART",
        )
        arcpy.management.Dissolve(
            in_features=self.files["arealdekke_samferdsel"],
            out_feature_class=self.files["arealdekke_samferdsel_dissolved"],
            dissolve_field=["arealdekke", self.index_col],
            multi_part="SINGLE_PART",
        )

    @timing_decorator
    def restore_data(self) -> None:
        """
        Restores data to the dissolved features.
        """
        self.restore_data_polygon_without_feature_to_point(
            self.files["arealdekke_snaumark_dissolved"],
            self.files["arealdekke_snaumark"],
            "dgfcd_feature_alpha",
            self.index_col,
        )
        self.restore_data_polygon_without_feature_to_point(
            self.files["arealdekke_not_snau_dissolved"],
            self.files["arealdekke_not_snau"],
            "arealdekke",
            self.index_col,
        )
        self.restore_data_polygon_without_feature_to_point(
            self.files["arealdekke_samferdsel_dissolved"],
            self.files["arealdekke_samferdsel"],
            "arealdekke",
            self.index_col,
            index_bool=True,
        )

        arcpy.management.Merge(
            inputs=[
                self.files["arealdekke_snaumark_dissolved"],
                self.files["arealdekke_not_snau_dissolved"],
                self.files["arealdekke_samferdsel_dissolved"],
                self.files["arealdekke_gangogsykkel"],
            ],
            output=self.output_feature,
        )

    @staticmethod
    def restore_data_polygon_without_feature_to_point(
        without_data: str,
        original: str,
        column: str,
        index: str,
        index_bool: bool = False,
    ) -> None:
        """
        Restore function for polygons when featureToPoint doesnt work.
        Restore data in without_data from original.
        Chooses biggest of intersecting polygons from original with matching values in column.
        """

        near_table = "in_memory\\near_table"
        arcpy.analysis.GenerateNearTable(
            in_features=without_data,
            near_features=original,
            out_table=near_table,
            closest="ALL",
            search_radius="0 Meters",
        )

        # build maps for faster access later:
        in_fid_near_fid = defaultdict(list)

        with arcpy.da.SearchCursor(near_table, ["IN_FID", "NEAR_FID"]) as cursor:
            for row in cursor:
                in_fid_near_fid[row[0]].append(row[1])

        column_map = {}
        area_map = {}
        index_map = {}
        with arcpy.da.SearchCursor(
            original, ["OID@", column, "SHAPE@AREA", index]
        ) as a_cur:
            for a_row in a_cur:
                column_map[a_row[0]] = a_row[1]
                area_map[a_row[0]] = a_row[2]
                index_map[a_row[0]] = a_row[3]

        # find biggest intersecting polygon with matching column value and index value if index_bool is true, and save the fid of that polygon for each dissolved polygon:
        fields = ["OID@", column] + ([index] if index_bool else [])

        with arcpy.da.SearchCursor(without_data, fields) as d_cur:
            for d_row in d_cur:
                oid = d_row[0]
                col_d = d_row[1]
                index_d = d_row[2] if index_bool else None

                near_fids = in_fid_near_fid.get(oid, [])
                best_fid = None
                biggest = 0

                for fid in near_fids:
                    col_a = column_map.get(fid)
                    area = area_map.get(fid, 0)
                    index_a = index_map.get(fid)

                    if col_d != col_a:
                        continue

                    if index_bool and index_a != index_d:
                        continue

                    if area > biggest:
                        biggest = area
                        best_fid = fid

                if best_fid is not None:
                    in_fid_near_fid[oid] = [best_fid]

        # Add fields from original to without_data and populate them based on the best_fid for each dissolved polygon:
        orig_fields = [
            f.name
            for f in arcpy.ListFields(original)
            if not f.required and f.type != "Geometry"
        ]

        orig_alias = [
            f.aliasName
            for f in arcpy.ListFields(original)
            if not f.required and f.type != "Geometry"
        ]

        target_fields = [
            f.name
            for f in arcpy.ListFields(without_data)
            if not f.required and f.type != "Geometry"
        ]

        for field in target_fields:
            arcpy.management.DeleteField(without_data, field)

        for fld, alias in zip(orig_fields, orig_alias):
            arcpy.management.AddField(
                without_data,
                fld,
                arcpy.ListFields(original, fld)[0].type,
                field_alias=alias,
            )

        # build a map of original attributes for faster access later:
        orig_oid_field = arcpy.Describe(original).OIDFieldName
        orig_attr = {}
        fields = [orig_oid_field] + orig_fields
        with arcpy.da.SearchCursor(original, fields) as cur:
            for row in cur:
                orig_attr[row[0]] = row[1:]

        # populate fields in without_data with orig attributes:
        dissolved_oid_field = arcpy.Describe(without_data).OIDFieldName
        update_fields = [dissolved_oid_field] + orig_fields
        with arcpy.da.UpdateCursor(without_data, update_fields) as ucur:
            for urow in ucur:
                in_fid = urow[0]
                orig_oid_list = in_fid_near_fid.get(in_fid)
                orig_oid = orig_oid_list[0] if orig_oid_list else None
                if orig_oid and orig_oid in orig_attr:
                    for i, val in enumerate(orig_attr[orig_oid], start=1):
                        urow[i] = val
                    ucur.updateRow(urow)

        for field in target_fields:
            if field not in orig_fields:
                arcpy.management.DeleteField(without_data, field)

    @timing_decorator
    def run(self) -> None:
        environment_setup.main()
        self.fetch_divide_data()
        self.dissolve()
        self.restore_data()
        self.geometry_validator.check_repair_sequence(
            input_fc=self.output_feature, max_iterations=5
        )
        self.wfm.delete_created_files()


def normal_call(input_fc: str, output_fc: str):
    identity = "in_memory\\arealdekke_identity"
    arcpy.analysis.Identity(
        in_features=input_fc,
        identity_features=input_n10.Fishnet_500m,
        out_feature_class=identity,
        join_attributes="ONLY_FID",
    )

    areal_dekke_config = logic_config.ArealDekkeDissolverInitKwargs(
        input_feature=identity,
        output_feature=output_fc,
        index_column_name="FID_Fishnet_500m",
        work_file_manager_config=core_config.WorkFileConfig(
            root_file=Arealdekke_N10.dissolve_arealdekke_root.value
        ),
    )
    ArealdekkeDissolver(areal_dekke_dissolver_config=areal_dekke_config).run()


def partition_call(input_fc: str, output_fc: str, map_scale: str):
    identity = "in_memory\\arealdekke_identity"
    arcpy.analysis.Identity(  # Resultatet ble bedre når identity ble kjørt utenfor partition iterator. Identity brukes bare for samferdsel tror jeg.
        in_features=input_fc,
        identity_features=input_n10.Fishnet_500m,
        out_feature_class=identity,
        join_attributes="ONLY_FID",
    )
    arealdekke = "arealdekke"
    dissolved_arealdekke = "dissolved_arealdekke"
    partition_area_input_config = core_config.PartitionInputConfig(
        entries=[
            core_config.InputEntry.processing_input(
                object=arealdekke,
                path=identity,
            )
        ]
    )

    partition_area_output_config = core_config.PartitionOutputConfig(
        entries=[
            core_config.OutputEntry.vector_output(
                object=arealdekke,
                tag=dissolved_arealdekke,
                path=output_fc,
            )
        ]
    )

    partiton_area_io_config = core_config.PartitionIOConfig(
        input_config=partition_area_input_config,
        output_config=partition_area_output_config,
        documentation_directory=Arealdekke_N10.areal_dissolve_documentation.value,
    )

    # Method Config:

    partiton_input = core_config.InjectIO(object=arealdekke, tag="input")
    partition_output = core_config.InjectIO(object=arealdekke, tag=dissolved_arealdekke)

    arealdekke_init_config = logic_config.ArealDekkeDissolverInitKwargs(
        input_feature=partiton_input,
        output_feature=partition_output,
        index_column_name="FID_Fishnet_500m",
        work_file_manager_config=core_config.WorkFileConfig(
            root_file=Arealdekke_N10.dissolve_arealdekke_root.value
        ),
        map_scale=map_scale,
    )
    arealdekke_method = core_config.ClassMethodEntryConfig(
        class_=ArealdekkeDissolver,
        method=ArealdekkeDissolver.run,
        init_params=arealdekke_init_config,
    )
    partition_area_method_config = core_config.MethodEntriesConfig(
        entries=[arealdekke_method]
    )

    # Run Config:
    partiton_area_run_config = core_config.PartitionRunConfig(
        max_elements_per_partition=50_000,
        context_radius_meters=0,
        run_partition_optimization=False,
    )

    # WorkFileConfig:
    partiton_area_workfile_config = core_config.WorkFileConfig(
        root_file=Arealdekke_N10.dissolve_arealdekke_partition_root.value
    )

    # PartitionIterator Config:
    partition_areal_dissolve = PartitionIterator(
        partition_io_config=partiton_area_io_config,
        partition_method_inject_config=partition_area_method_config,
        partition_iterator_run_config=partiton_area_run_config,
        work_file_manager_config=partiton_area_workfile_config,
    )

    partition_areal_dissolve.run()
