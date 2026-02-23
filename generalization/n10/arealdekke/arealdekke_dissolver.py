import arcpy

from custom_tools.decorators.timing_decorator import timing_decorator

from composition_configs import core_config
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from input_data import input_n10
from env_setup import environment_setup

from custom_tools.general_tools.partition_iterator import PartitionIterator

from collections import defaultdict

from composition_configs import core_config, logic_config


class ArealdekkeDissolver:
    """
    ArealdekkeDissolver.
    """

    def __init__(
        self, areal_dekke_dissolver_config: logic_config.ArealDekkeDissolverInitKwargs
    ):
        self.input_arealdekke = areal_dekke_dissolver_config.input_feature
        self.output_feature = areal_dekke_dissolver_config.output_feature

        self.index_col = areal_dekke_dissolver_config.index_column_name

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
        arealdekke_ikke_snau = wfm.build_file_path(
            file_name="arealdekke_ikke_snau", file_type="gdb"
        )
        arealdekke_ikke_snau_dissolved = wfm.build_file_path(
            file_name="arealdekke_ikke_snau_dissolved", file_type="gdb"
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
        fishnet = wfm.build_file_path(file_name="fishnet", file_type="gdb")
        arealdekke_identity = wfm.build_file_path(
            file_name="arealdekke_identity", file_type="gdb"
        )
        arealdekke_gangogsykkel = wfm.build_file_path(
            file_name="arealdekke_gangogsykkel", file_type="gdb"
        )
        arealdekke_gangogsykkel_clipped = wfm.build_file_path(
            file_name="arealdekke_gangogsykkel_clipped", file_type="gdb"
        )
        arealdekke_gangogsykkel_erased = wfm.build_file_path(
            file_name="arealdekke_gangogsykkel_erased", file_type="gdb"
        )
        arealdekke_samferdsel_dissolved_buffer = wfm.build_file_path(
            file_name="arealdekke_samferdsel_dissolved_buffer", file_type="gdb"
        )
        arealdekke_samferdsel_dissolved_gangogsykkel = wfm.build_file_path(
            file_name="arealdekke_samferdsel_dissolved_gangogsykkel", file_type="gdb"
        )
        arealdekke_gangogsykkel_erased_dissolved = wfm.build_file_path(
            file_name="arealdekke_gangogsykkel_erased_dissolved", file_type="gdb"
        )
        arealdekke_gangogsykkel_clipped_dissolved = wfm.build_file_path(
            file_name="arealdekke_gangogsykkel_clipped_dissolved", file_type="gdb"
        )

        return {
            "arealdekke_input": arealdekke_input,
            "arealdekke_snaumark": arealdekke_snaumark,
            "arealdekke_snaumark_dissolved": arealdekke_snaumark_dissolved,
            "arealdekke_ikke_snau": arealdekke_ikke_snau,
            "arealdekke_ikke_snau_dissolved": arealdekke_ikke_snau_dissolved,
            "arealdekke_dissolved_Norge": arealdekke_dissolved_Norge,
            "arealdekke_samferdsel": arealdekke_samferdsel,
            "arealdekke_samferdsel_dissolved": arealdekke_samferdsel_dissolved,
            "fishnet": fishnet,
            "arealdekke_identity": arealdekke_identity,
            "arealdekke_gangogsykkel": arealdekke_gangogsykkel,
            "arealdekke_samferdsel_dissolved_buffer": arealdekke_samferdsel_dissolved_buffer,
            "arealdekke_gangogsykkel_clipped": arealdekke_gangogsykkel_clipped,
            "arealdekke_gangogsykkel_erased": arealdekke_gangogsykkel_erased,
            "arealdekke_samferdsel_dissolved_gangogsykkel": arealdekke_samferdsel_dissolved_gangogsykkel,
            "arealdekke_gangogsykkel_erased_dissolved": arealdekke_gangogsykkel_erased_dissolved,
            "arealdekke_gangogsykkel_clipped_dissolved": arealdekke_gangogsykkel_clipped_dissolved,
        }

    @timing_decorator
    def fetch_divide_data(self) -> None:
        print("starting fetch and divide data")
        print("Copy")
        arcpy.management.CopyFeatures(
            in_features=self.input_arealdekke,
            out_feature_class=self.files["arealdekke_input"],
        )
        print("identity")
        arcpy.analysis.Identity(
            in_features=self.files["arealdekke_input"],
            identity_features=input_n10.Fishnet_500m,
            out_feature_class=self.files["arealdekke_identity"],
            join_attributes="ONLY_FID",
        )

        snaumark = "snaumark"
        ikke_snau = "ikke_snau"
        samferdsel = "samferdsel"
        print("1")
        arcpy.management.MakeFeatureLayer(
            in_features=self.files["arealdekke_identity"],
            out_layer=snaumark,
            where_clause="arealdekke IN ('Snaumark_frisk', 'Snaumark_impediment', 'Snaumark_konstruert', 'Snaumark_middels_frisk', 'Snaumark_skrinn', 'Snaumark_uspesifisert')",
        )
        print("2")
        arcpy.management.MakeFeatureLayer(
            in_features=self.files["arealdekke_identity"],
            out_layer=ikke_snau,
            where_clause="arealdekke NOT IN ('Snaumark_frisk', 'Snaumark_impediment', 'Snaumark_konstruert', 'Snaumark_middels_frisk', 'Snaumark_skrinn', 'Snaumark_uspesifisert', 'Samferdsel')",
        )
        print("3")
        arcpy.management.MakeFeatureLayer(
            in_features=self.files["arealdekke_identity"],
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
        print("4")
        arcpy.management.CopyFeatures(
            in_features=snaumark, out_feature_class=self.files["arealdekke_snaumark"]
        )
        print("5")
        arcpy.management.CopyFeatures(
            in_features=ikke_snau, out_feature_class=self.files["arealdekke_ikke_snau"]
        )
        print("6")
        arcpy.management.CopyFeatures(
            in_features=samferdsel,
            out_feature_class=self.files["arealdekke_samferdsel"],
        )

    @timing_decorator
    def dissolve(self) -> None:
        print("starting dissolve")
        print("1")
        ikke_snau_dis_mem = "in_memory\\ikke_snau_dis_mem"
        arcpy.management.Dissolve(
            in_features=self.files["arealdekke_ikke_snau"],
            out_feature_class=ikke_snau_dis_mem,
            dissolve_field=["arealdekke", self.index_col],
            multi_part="SINGLE_PART",
        )
        print("2")
        arcpy.management.Dissolve(
            in_features=ikke_snau_dis_mem,
            out_feature_class=self.files["arealdekke_ikke_snau_dissolved"],
            dissolve_field=["arealdekke"],
            multi_part="SINGLE_PART",
        )

        snau_dis_mem = "in_memory\\snau_dis_mem"
        print("3")
        arcpy.management.Dissolve(
            in_features=self.files["arealdekke_snaumark"],
            out_feature_class=snau_dis_mem,
            dissolve_field=["dgfcd_feature_alpha", self.index_col],
            multi_part="SINGLE_PART",
        )
        print("4")
        arcpy.management.Dissolve(
            in_features=snau_dis_mem,
            out_feature_class=self.files["arealdekke_snaumark_dissolved"],
            dissolve_field=["dgfcd_feature_alpha"],
            multi_part="SINGLE_PART",
        )
        print("5")
        arcpy.management.Dissolve(
            in_features=self.files["arealdekke_samferdsel"],
            out_feature_class=self.files["arealdekke_samferdsel_dissolved"],
            dissolve_field=["arealdekke", self.index_col],
            multi_part="SINGLE_PART",
        )

    @timing_decorator
    def gang_sykkel(self) -> None:
        arcpy.analysis.Buffer(
            in_features=self.files["arealdekke_samferdsel_dissolved"],
            out_feature_class=self.files["arealdekke_samferdsel_dissolved_buffer"],
            buffer_distance_or_field="5 Meters",
        )
        arcpy.analysis.Clip(
            in_features=self.files["arealdekke_gangogsykkel"],
            clip_features=self.files["arealdekke_samferdsel_dissolved_buffer"],
            out_feature_class=self.files["arealdekke_gangogsykkel_clipped"],
        )
        arcpy.analysis.Erase(
            in_features=self.files["arealdekke_gangogsykkel"],
            erase_features=self.files["arealdekke_samferdsel_dissolved_buffer"],
            out_feature_class=self.files["arealdekke_gangogsykkel_erased"],
        )
        arcpy.management.Dissolve(
            in_features=self.files["arealdekke_gangogsykkel_clipped"],
            out_feature_class=self.files["arealdekke_gangogsykkel_clipped_dissolved"],
            dissolve_field=["arealdekke", self.index_col],
            multi_part="SINGLE_PART",
        )
        arcpy.management.Append(
            inputs=[self.files["arealdekke_gangogsykkel_clipped_dissolved"]],
            target=self.files["arealdekke_samferdsel_dissolved"],
        )
        arcpy.management.Dissolve(
            in_features=self.files["arealdekke_samferdsel_dissolved"],
            out_feature_class=self.files[
                "arealdekke_samferdsel_dissolved_gangogsykkel"
            ],
            dissolve_field=["arealdekke", self.index_col],
            multi_part="SINGLE_PART",
        )

    def create_fishnet(self):
        layer = "norway"
        arcpy.management.MakeFeatureLayer(
            in_features=input_n10.AdminFlate, out_layer=layer
        )

        out_sr = arcpy.Describe(input_n10.AdminFlate).spatialReference

        proj_norway = arcpy.management.Project(
            "norway", "in_memory/norway_proj", out_sr
        )
        desc = arcpy.Describe(proj_norway)
        ext = desc.extent
        xmin, ymin, xmax, ymax = ext.XMin, ext.YMin, ext.XMax, ext.YMax

        origin_coord = f"{xmin} {ymin}"
        y_axis_coord = f"{xmin} {ymin + 10}"

        arcpy.management.CreateFishnet(
            out_feature_class=r"C:\GIS_Files\ag_inputs\n10.gdb\Fishnet_500m",
            origin_coord=origin_coord,
            y_axis_coord=y_axis_coord,
            cell_width="500",
            cell_height="500",
            corner_coord=f"{xmax} {ymax}",
            labels="NO_LABELS",
            template=proj_norway,
            geometry_type="POLYGON",
        )

        arcpy.management.MakeFeatureLayer(
            in_features=r"C:\GIS_Files\ag_inputs\n10.gdb\Fishnet_500m",
            out_layer="fish_layer",
        )
        arcpy.management.SelectLayerByLocation(
            in_layer="fish_layer",
            overlap_type="INTERSECT",
            select_features=input_n10.AdminFlate,
            selection_type="NEW_SELECTION",
            invert_spatial_relationship="INVERT",
        )
        arcpy.management.DeleteFeatures(in_features="fish_layer")

    @timing_decorator
    def restore_data(self) -> None:
        # DEtte er litt rart se om det er en bedre måte å gjøre det på (altså gang og sykkel som blir appendet) Du må også dissolve de små bitene i clipped som ikke blir kombinert med vei, sammen med gang og sykkelveg fra erased
        arcpy.management.Append(
            inputs=[self.files["arealdekke_gangogsykkel"]],
            target=self.files["arealdekke_samferdsel"],
        )
        dissolved_input_list = [
            [
                self.files["arealdekke_snaumark_dissolved"],
                self.files["arealdekke_snaumark"],
                "dgfcd_feature_alpha",
            ],
            [
                self.files["arealdekke_ikke_snau_dissolved"],
                self.files["arealdekke_ikke_snau"],
                "arealdekke",
            ],
            [
                self.files["arealdekke_samferdsel_dissolved_gangogsykkel"],
                self.files["arealdekke_samferdsel"],
                "arealdekke",
            ],
        ]

        for dissolved_input_col in dissolved_input_list:
            print("restoring data for " + dissolved_input_col[0])
            dissolved = dissolved_input_col[0]
            orig = dissolved_input_col[1]
            column = dissolved_input_col[2]
            print("starting near table")
            near_table = "in_memory\\near_table"
            arcpy.analysis.GenerateNearTable(
                in_features=dissolved,
                near_features=orig,
                out_table=near_table,
                closest="ALL",
                closest_count=10,
                search_radius="0 Meters",
            )
            print("near table done")

            in_fid_near_fid = defaultdict(list)

            with arcpy.da.SearchCursor(near_table, ["IN_FID", "NEAR_FID"]) as cursor:
                for row in cursor:
                    in_fid_near_fid[row[0]].append(row[1])

            column_map = {}
            area_map = {}
            with arcpy.da.SearchCursor(orig, ["OID@", column, "SHAPE@AREA"]) as a_cur:
                for a_row in a_cur:
                    column_map[a_row[0]] = a_row[1]
                    area_map[a_row[0]] = a_row[2]

            with arcpy.da.SearchCursor(dissolved, ["OID@", column]) as d_cur:
                for d_row in d_cur:
                    oid = d_row[0]
                    col_d = d_row[1]

                    near_fids = in_fid_near_fid.get(oid, [])
                    biggest = 0
                    for fid in near_fids:
                        col_a = column_map.get(fid)
                        area = area_map.get(fid)

                        if col_d != col_a:
                            continue

                        if area < biggest:
                            continue

                        biggest = area
                        in_fid_near_fid[oid] = [fid]

            orig_fields = [
                f.name
                for f in arcpy.ListFields(orig)
                if not f.required and f.type != "Geometry"
            ]

            orig_alias = [
                f.aliasName
                for f in arcpy.ListFields(orig)
                if not f.required and f.type != "Geometry"
            ]

            target_fields = [
                f.name
                for f in arcpy.ListFields(dissolved)
                if not f.required and f.type != "Geometry"
            ]

            for field in target_fields:
                arcpy.management.DeleteField(dissolved, field)

            for fld, alias in zip(orig_fields, orig_alias):
                arcpy.management.AddField(
                    dissolved,
                    fld,
                    arcpy.ListFields(orig, fld)[0].type,
                    field_alias=alias,
                )

            orig_oid_field = arcpy.Describe(orig).OIDFieldName
            orig_attr = {}
            fields = [orig_oid_field] + orig_fields
            with arcpy.da.SearchCursor(orig, fields) as cur:
                for row in cur:
                    orig_attr[row[0]] = row[1:]

            dissolved_oid_field = arcpy.Describe(dissolved).OIDFieldName
            update_fields = [dissolved_oid_field] + orig_fields
            with arcpy.da.UpdateCursor(dissolved, update_fields) as ucur:
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
                    arcpy.management.DeleteField(dissolved, field)

        arcpy.management.Merge(
            inputs=[
                self.files["arealdekke_snaumark_dissolved"],
                self.files["arealdekke_ikke_snau_dissolved"],
                self.files["arealdekke_samferdsel_dissolved_gangogsykkel"],
                self.files["arealdekke_gangogsykkel_erased"],
            ],
            output=self.output_feature,
        )

    @timing_decorator
    def run(self) -> None:
        environment_setup.main()
        self.fetch_divide_data()
        self.dissolve()
        self.gang_sykkel()
        self.restore_data()
        self.wfm.delete_created_files()


def normal_call():

    areal_dekke_config = logic_config.ArealDekkeDissolverInitKwargs(
        input_feature=input_n10.Arealdekke_Oslo,
        output_feature=Arealdekke_N10.dissolve_arealdekke.value,
        index_column_name="FID_Fishnet_500m",
        work_file_manager_config=core_config.WorkFileConfig(
            root_file=Arealdekke_N10.dissolve_arealdekke_root.value
        ),
    )
    ArealdekkeDissolver(areal_dekke_dissolver_config=areal_dekke_config).run()


def partition_call():
    arealdekke = "arealdekke"
    dissolved_arealdekke = "dissolved_arealdekke"
    partition_area_input_config = core_config.PartitionInputConfig(
        entries=[
            core_config.InputEntry.processing_input(
                object=arealdekke,
                path=input_n10.Arealdekke_Oslo,
            )
        ]
    )

    partition_area_output_config = core_config.PartitionOutputConfig(
        entries=[
            core_config.OutputEntry.vector_output(
                object=arealdekke,
                tag=dissolved_arealdekke,
                path=Arealdekke_N10.dissolve_arealdekke.value,
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
        context_radius_meters=100,
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


if __name__ == "__main__":
    normal_call()
    partition_call()

