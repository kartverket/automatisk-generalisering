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
        }

    @timing_decorator
    def fetch_divide_data(self) -> None:
        arcpy.management.CopyFeatures(
            in_features=self.input_arealdekke,
            out_feature_class=self.files["arealdekke_input"],
        )
        
        

        snaumark = "snaumark"
        ikke_snau = "ikke_snau"
        samferdsel = "samferdsel"
        arcpy.management.MakeFeatureLayer(
            in_features=self.files["arealdekke_input"],
            out_layer=snaumark,
            where_clause="arealdekke IN ('Snaumark_frisk', 'Snaumark_impediment', 'Snaumark_konstruert', 'Snaumark_middels_frisk', 'Snaumark_skrinn', 'Snaumark_uspesifisert')",
        )
        arcpy.management.MakeFeatureLayer(
            in_features=self.files["arealdekke_input"],
            out_layer=ikke_snau,
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
            in_features=ikke_snau, out_feature_class=self.files["arealdekke_ikke_snau"]
        )
        arcpy.management.CopyFeatures(
            in_features=samferdsel,
            out_feature_class=self.files["arealdekke_samferdsel"],
        )

    @timing_decorator
    def dissolve(self) -> None:

        ikke_snau_dis_mem = "in_memory\\ikke_snau_dis_mem"
        arcpy.management.Dissolve(
            in_features=self.files["arealdekke_ikke_snau"],
            out_feature_class=ikke_snau_dis_mem,
            dissolve_field=["arealdekke", self.index_col],
            multi_part="SINGLE_PART",
        )
        arcpy.management.Dissolve(
            in_features=ikke_snau_dis_mem,
            out_feature_class=self.files["arealdekke_ikke_snau_dissolved"],
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

        self.restore_data_polygon_without_feature_to_point(self.files["arealdekke_snaumark_dissolved"], self.files["arealdekke_snaumark"], "dgfcd_feature_alpha", self.index_col)
        self.restore_data_polygon_without_feature_to_point(self.files["arealdekke_ikke_snau_dissolved"], self.files["arealdekke_ikke_snau"], "arealdekke", self.index_col)
        self.restore_data_polygon_without_feature_to_point(self.files["arealdekke_samferdsel_dissolved"], self.files["arealdekke_samferdsel"], "arealdekke", self.index_col, index_bool=True)
            
           

        arcpy.management.Merge(
            inputs=[
                self.files["arealdekke_snaumark_dissolved"],
                self.files["arealdekke_ikke_snau_dissolved"],
                self.files["arealdekke_samferdsel_dissolved_gangogsykkel"],
                self.files["arealdekke_gangogsykkel_erased"],
            ],
            output=self.output_feature,
        )
    
    @staticmethod
    def restore_data_polygon_without_feature_to_point(without_data: str, original: str, column: str, index: str, index_bool: bool = False) -> None:
        """
        For when featureToPoint doesnt work.
        Restore data in without_data from original. 
        Chooses biggest of  intersecting polygons from original with matching values in column.
        """
         
        near_table = "in_memory\\near_table"
        arcpy.analysis.GenerateNearTable(
            in_features=without_data,
            near_features=original,
            out_table=near_table,
            closest="ALL",
            search_radius="0 Meters",
        )

        in_fid_near_fid = defaultdict(list)

        with arcpy.da.SearchCursor(near_table, ["IN_FID", "NEAR_FID"]) as cursor:
            for row in cursor:
                in_fid_near_fid[row[0]].append(row[1])

        column_map = {}
        area_map = {}
        index_map = {}
        with arcpy.da.SearchCursor(original, ["OID@", column, "SHAPE@AREA", index]) as a_cur:
            for a_row in a_cur:
                column_map[a_row[0]] = a_row[1]
                area_map[a_row[0]] = a_row[2]
                index_map[a_row[0]] = a_row[3]

        if index_bool:
            with arcpy.da.SearchCursor(without_data, ["OID@", column, index]) as d_cur:
                for d_row in d_cur:
                    oid = d_row[0]
                    col_d = d_row[1]
                    index_d = d_row[2]

                    near_fids = in_fid_near_fid.get(oid, [])
                    biggest = 0
                    for fid in near_fids:
                        col_a = column_map.get(fid)
                        area = area_map.get(fid)
                        index_a = index_map.get(fid)

                        if col_d != col_a:
                            continue

                        if area < biggest:
                            continue

                        if index_a != index_d:
                            continue

                        biggest = area
                        in_fid_near_fid[oid] = [fid]
        else:
            with arcpy.da.SearchCursor(without_data, ["OID@", column]) as d_cur:
                for d_row in d_cur:
                    oid = d_row[0]
                    col_d = d_row[1]

                    near_fids = in_fid_near_fid.get(oid, [])
                    biggest = 0
                    for fid in near_fids:
                        col_a = column_map.get(fid)
                        area = area_map.get(fid)
                        index_a = index_map.get(fid)

                        if col_d != col_a:
                            continue

                        if area < biggest:
                            continue

                        biggest = area
                        in_fid_near_fid[oid] = [fid]


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

        orig_oid_field = arcpy.Describe(original).OIDFieldName
        orig_attr = {}
        fields = [orig_oid_field] + orig_fields
        with arcpy.da.SearchCursor(original, fields) as cur:
            for row in cur:
                orig_attr[row[0]] = row[1:]

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
    def repair_geom(self):
        arcpy.management.RepairGeometry(in_features=self.output_feature, delete_null="DELETE_NULL", validation_method="ESRI")

    @timing_decorator
    def run(self) -> None:
        environment_setup.main()
        self.fetch_divide_data()
        self.dissolve()
        self.restore_data()
        self.repair_geom()
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
    identity = "in_memory\\arealdekke_identity"
    arcpy.analysis.Identity(                                ################################ Resultatet ble bedre når identity ble kjørt utenfor partition iterator. ################################
        in_features=input_n10.Arealdekke_Oslo,
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


class GangSykkelDissolver:
    def __init__(self, gang_sykkel_dissolver_config: logic_config.GangSykkelDissolverInitKwargs):
        self.input_gangsykkel = gang_sykkel_dissolver_config.input_feature
        self.output_feature = gang_sykkel_dissolver_config.output_feature

        self.index_col = gang_sykkel_dissolver_config.index_column_name

        self.wfm = WorkFileManager(
            config=gang_sykkel_dissolver_config.work_file_manager_config
        )
        self.files = self.create_wfm_gdbs(self.wfm)
        


    def create_wfm_gdbs(self, wfm: WorkFileManager) -> dict:
        gangsykkel_input = wfm.build_file_path(file_name="gangsykkel_input", file_type="gdb")
        gangsykkel_samferdsel = wfm.build_file_path(file_name="gangsykkel_samferdsel", file_type="gdb")
        gangsykkel_samferdsel_buffer = wfm.build_file_path(file_name="gangsykkel_samferdsel_buffer", file_type="gdb")
        gangsykkel_gangsykkel = wfm.build_file_path(file_name="gangsykkel_gangsykkel", file_type="gdb")
        gangsykkel_gangsykkel_clipped = wfm.build_file_path(file_name="gangsykkel_gangsykkel_clipped", file_type="gdb")
        gangsykkel_gangsykkel_erased = wfm.build_file_path(file_name="gangsykkel_gangsykkel_erased", file_type="gdb")
        gangsykkel_gangsykkel_clipped_dissolved = wfm.build_file_path(file_name="gangsykkel_gangsykkel_clipped_dissolved", file_type="gdb")
        gangsykkel_samferdsel_gangsykkel_dissolved = wfm.build_file_path(file_name="gangsykkel_samferdsel_gangsykkel_dissolved", file_type="gdb")
        gangsykkel_ikke_samferdsel = wfm.build_file_path(file_name="gangsykkel_ikke_samferdsel", file_type="gdb")
        gangsykkel_gangsykkel_clipped_singlepart = wfm.build_file_path(file_name="gangsykkel_gangsykkel_clipped_singlepart", file_type="gdb")

        return {
            "gangsykkel_input": gangsykkel_input,
            "gangsykkel_samferdsel": gangsykkel_samferdsel,
            "gangsykkel_samferdsel_buffer": gangsykkel_samferdsel_buffer,
            "gangsykkel_gangsykkel": gangsykkel_gangsykkel,
            "gangsykkel_gangsykkel_clipped": gangsykkel_gangsykkel_clipped,
            "gangsykkel_gangsykkel_erased": gangsykkel_gangsykkel_erased,
            "gangsykkel_gangsykkel_clipped_dissolved": gangsykkel_gangsykkel_clipped_dissolved,
            "gangsykkel_samferdsel_gangsykkel_dissolved": gangsykkel_samferdsel_gangsykkel_dissolved,
            "gangsykkel_ikke_samferdsel": gangsykkel_ikke_samferdsel,
            "gangsykkel_gangsykkel_clipped_singlepart": gangsykkel_gangsykkel_clipped_singlepart,
        }

    def fetch_data(self):
        arcpy.management.CopyFeatures(
            in_features=self.input_gangsykkel,
            out_feature_class=self.files["gangsykkel_input"]
        )

        samferdsel = "layer_samferdsel"
        arcpy.management.MakeFeatureLayer(
            in_features=self.files["gangsykkel_input"],
            out_layer=samferdsel,
            where_clause="arealdekke = 'Samferdsel' AND arealbruk_underklasse <> 'GangSykkelVeg'"
        )
        arcpy.management.CopyFeatures(
            in_features=samferdsel,
            out_feature_class=self.files["gangsykkel_samferdsel"]
        )

        gangsykkel = "layer_gangsykkel"
        arcpy.management.MakeFeatureLayer(
            in_features=self.files["gangsykkel_input"],
            out_layer=gangsykkel,
            where_clause="arealdekke = 'Samferdsel' AND arealbruk_underklasse = 'GangSykkelVeg'"
        )
        arcpy.management.CopyFeatures(
            in_features=gangsykkel,
            out_feature_class=self.files["gangsykkel_gangsykkel"]
        )

        ikke_samferdsel = "layer_ikke_samferdsel"
        arcpy.management.MakeFeatureLayer(
            in_features=self.files["gangsykkel_input"],
            out_layer=ikke_samferdsel,
            where_clause="arealdekke <> 'Samferdsel'"
        )
        arcpy.management.CopyFeatures(
            in_features=ikke_samferdsel,
            out_feature_class=self.files["gangsykkel_ikke_samferdsel"]
        )



    @timing_decorator
    def dissolve(self) -> None:
        arcpy.analysis.Buffer(
            in_features=self.files["gangsykkel_samferdsel"],
            out_feature_class=self.files["gangsykkel_samferdsel_buffer"],
            buffer_distance_or_field="5 Meters",
        )
        arcpy.analysis.Clip(
            in_features=self.files["gangsykkel_gangsykkel"],
            clip_features=self.files["gangsykkel_samferdsel_buffer"],
            out_feature_class=self.files["gangsykkel_gangsykkel_clipped"]
        )
        arcpy.management.MultipartToSinglepart(
            in_features=self.files["gangsykkel_gangsykkel_clipped"],
            out_feature_class=self.files["gangsykkel_gangsykkel_clipped_singlepart"]
        )
        arcpy.analysis.Erase(
            in_features=self.files["gangsykkel_gangsykkel"],
            erase_features=self.files["gangsykkel_samferdsel_buffer"],
            out_feature_class=self.files["gangsykkel_gangsykkel_erased"]
        )
        """arcpy.management.Dissolve(
            in_features=self.files["gangsykkel_gangsykkel_clipped"],
            out_feature_class=self.files["gangsykkel_gangsykkel_clipped_dissolved"],
            dissolve_field=["arealdekke", self.index_col],
            multi_part="SINGLE_PART"
        )"""
        gangsykkel_length_25 = "layer_gangsykkel_length_25"
        arcpy.management.MakeFeatureLayer(
            in_features=self.files["gangsykkel_gangsykkel_clipped"],
            out_layer= gangsykkel_length_25,
            where_clause='"Shape_Length" > 25'
        )
        gangsykkel_length_not_25 = "layer_gangsykkel_length_not_25"
        arcpy.management.MakeFeatureLayer(
            in_features=self.files["gangsykkel_gangsykkel_clipped"],
            out_layer= gangsykkel_length_not_25,
            where_clause='"Shape_Length" <= 25'
        )

        arcpy.management.Append(
            inputs=[gangsykkel_length_25],
            target=self.files["gangsykkel_samferdsel"],
        )
        arcpy.management.Append(
            inputs=[gangsykkel_length_not_25],
            target=self.files["gangsykkel_gangsykkel_erased"],
        )


        arcpy.management.Dissolve(
            in_features=self.files["gangsykkel_samferdsel"],
            out_feature_class=self.files["gangsykkel_samferdsel_gangsykkel_dissolved"],
            dissolve_field=["arealdekke", self.index_col],
            multi_part="SINGLE_PART"
        )

    @timing_decorator
    def restore_data(self) -> None:
        ArealdekkeDissolver.restore_data_polygon_without_feature_to_point(self.files["gangsykkel_samferdsel_gangsykkel_dissolved"], self.files["gangsykkel_samferdsel"], "arealdekke", self.index_col, index_bool=True)

        arcpy.management.Merge(
            inputs=[
                self.files["gangsykkel_samferdsel_gangsykkel_dissolved"],
                self.files["gangsykkel_gangsykkel_erased"],
                self.files["gangsykkel_ikke_samferdsel"],
            ],
            output=self.output_feature,
        )



    @timing_decorator
    def run(self) -> None:
        environment_setup.main()
        self.fetch_data()
        self.dissolve()
        self.restore_data()
        self.wfm.delete_created_files()


def partition_call_gangsykkel(input_file, output_file):
    gangsykkel = "gangsykkel"
    dissolved_gangsykkel = "dissolved_agangsykkel"
    partition_input_config = core_config.PartitionInputConfig(
        entries=[
            core_config.InputEntry.processing_input(
                object=gangsykkel,
                path=input_file,
            )
        ]
    )

    partition_output_config = core_config.PartitionOutputConfig(
        entries=[
            core_config.OutputEntry.vector_output(
                object=gangsykkel,
                tag=dissolved_gangsykkel,
                path=output_file,
            )
        ]
    )

    partiton_area_io_config = core_config.PartitionIOConfig(
        input_config=partition_input_config,
        output_config=partition_output_config,
        documentation_directory=Arealdekke_N10.areal_dissolve_documentation.value,
    )

    # Method Config:

    partiton_input = core_config.InjectIO(object=gangsykkel, tag="input")
    partition_output = core_config.InjectIO(object=gangsykkel, tag=dissolved_gangsykkel)

    gangsykkel_init_config = logic_config.GangSykkelDissolverInitKwargs(
        input_feature=partiton_input,
        output_feature=partition_output,
        index_column_name="FID_Fishnet_500m",
        work_file_manager_config=core_config.WorkFileConfig(
            root_file=Arealdekke_N10.dissolve_arealdekke_root.value
        ),
    )
    arealdekke_method = core_config.ClassMethodEntryConfig(
        class_=GangSykkelDissolver,
        method=GangSykkelDissolver.run,
        init_params=gangsykkel_init_config,
    )
    partition_method_config = core_config.MethodEntriesConfig(
        entries=[arealdekke_method]
    )

    # Run Config:
    partiton_run_config = core_config.PartitionRunConfig(
        max_elements_per_partition=50_000,
        context_radius_meters=0,
        run_partition_optimization=False,
    )

    # WorkFileConfig:
    partiton_workfile_config = core_config.WorkFileConfig(
        root_file=Arealdekke_N10.dissolve_arealdekke_partition_root.value
    )

    # PartitionIterator Config:
    partition_gangsykkel_dissolve = PartitionIterator(
        partition_io_config=partiton_area_io_config,
        partition_method_inject_config=partition_method_config,
        partition_iterator_run_config=partiton_run_config,
        work_file_manager_config=partiton_workfile_config,
    )

    partition_gangsykkel_dissolve.run()    

class EliminateSmallPolygons:
    def __init__(self, eliminate_small_polygons_config: logic_config.EliminateSmallPolygonsInitKwargs):
        self.input_eliminate = eliminate_small_polygons_config.input_feature
        self.output_feature = eliminate_small_polygons_config.output_feature


        self.wfm = WorkFileManager(
            config=eliminate_small_polygons_config.work_file_manager_config
        )
        self.files = self.create_wfm_gdbs(self.wfm)

    def create_wfm_gdbs(self, wfm: WorkFileManager) -> dict:
        eliminate_input = wfm.build_file_path(file_name="eliminate_input", file_type="gdb")
        eliminate_eliminated = wfm.build_file_path(file_name="eliminate_eliminated", file_type="gdb")
        eliminate_after_elim = wfm.build_file_path(file_name="eliminate_after_elim", file_type="gdb")
        eliminate_selected_negative_buffers = wfm.build_file_path(file_name="eliminate_selected_negative_buffers", file_type="gdb")
        eliminate_selected_positive_buffers = wfm.build_file_path(file_name="eliminate_selected_positive_buffers", file_type="gdb")
        eliminate_clipped = wfm.build_file_path(file_name="eliminate_clipped", file_type="gdb")
        eliminate_erased = wfm.build_file_path(file_name="eliminate_erased", file_type="gdb")
        eliminate_erased_singlepart = wfm.build_file_path(file_name="eliminate_erased_singlepart", file_type="gdb")
        eliminate_merged_clipped_erased = wfm.build_file_path(file_name="eliminate_merged_clipped_erased", file_type="gdb")
        eliminate_clip_erase_eliminated = wfm.build_file_path(file_name="eliminate_clip_erase_eliminated", file_type="gdb")
        eliminate_final_elim = wfm.build_file_path(file_name="eliminate_final_elim", file_type="gdb")
        eliminate_clipped_singlepart = wfm.build_file_path(file_name="eliminate_clipped_singlepart", file_type="gdb")

        return {
            "eliminate_input": eliminate_input,
            "eliminate_eliminated": eliminate_eliminated,
            "eliminate_after_elim": eliminate_after_elim,
            "eliminate_selected_negative_buffers": eliminate_selected_negative_buffers,
            "eliminate_selected_positive_buffers": eliminate_selected_positive_buffers,
            "eliminate_clipped": eliminate_clipped,
            "eliminate_erased": eliminate_erased,
            "eliminate_erased_singlepart": eliminate_erased_singlepart,
            "eliminate_clipped_singlepart": eliminate_clipped_singlepart,
            "eliminate_merged_clipped_erased": eliminate_merged_clipped_erased,
            "eliminate_clip_erase_eliminated": eliminate_clip_erase_eliminated,
            "eliminate_final_elim": eliminate_final_elim,

        }
    
    def fetch_data(self):
        arcpy.management.CopyFeatures(
            in_features=self.input_eliminate,
            out_feature_class=self.files["eliminate_input"]
        )
    
    @timing_decorator
    def add_fields(self, input_fc):
        fields = [f.name for f in arcpy.ListFields(input_fc)]
        if "area" in fields:
            arcpy.management.DeleteField(input_fc, "area")
        if "length" in fields:
            arcpy.management.DeleteField(input_fc, "length")
        if "isoperimetric_quotient" in fields:
            arcpy.management.DeleteField(input_fc, "isoperimetric_quotient")
        if "iq_adjusted_area" in fields:
            arcpy.management.DeleteField(input_fc, "iq_adjusted_area")


        arcpy.management.AddField(
            in_table=input_fc,
            field_name="area",
            field_type="DOUBLE"
        )
        arcpy.management.CalculateField(
            in_table=input_fc,
            field="area",
            expression="!shape.area!",
            expression_type="PYTHON3"
        )
        arcpy.management.AddField(
            in_table=input_fc,
            field_name="length",
            field_type="DOUBLE"
        )
        arcpy.management.CalculateField(
            in_table=input_fc,
            field="length",
            expression="!shape.length!",
            expression_type="PYTHON3"
        )

        arcpy.management.AddField(
            in_table=input_fc,
            field_name="isoperimetric_quotient",
            field_type="DOUBLE"
        )
        arcpy.management.CalculateField(
            in_table=input_fc,
            field="isoperimetric_quotient",
            expression="(4 * 3.141592653589793 * !area!) / (!length! ** 2)",
            expression_type="PYTHON3"
        )
        arcpy.management.AddField(
            in_table=input_fc,
            field_name="iq_adjusted_area",
            field_type="DOUBLE"
        )
        arcpy.management.CalculateField(
            in_table=input_fc,
            field="iq_adjusted_area",
            expression="!area! * !isoperimetric_quotient!",
            expression_type="PYTHON3"
        )

        

    @timing_decorator
    def eliminate(self, input_fc, output_fc):
        layer = "eliminate_layer"
        arcpy.management.MakeFeatureLayer(
            in_features=input_fc, 
            out_layer=layer,
            where_clause="arealdekke <> 'Samferdsel' AND arealdekke <> 'Ferskvann_elv_bekk' AND arealdekke <> 'Ferskvann_kanal' AND area < 1500 AND iq_adjusted_area < 150"
        )

        arcpy.management.Eliminate(
            in_features=layer,
            out_feature_class=output_fc,
            selection = "LENGTH",
        )



    @timing_decorator
    def buffer_potential_spikes(self):
        layer = "eliminate_after_elim_layer" 
        arcpy.management.MakeFeatureLayer(
            in_features=self.files["eliminate_after_elim"], 
            out_layer=layer,
            where_clause="arealdekke <> 'Samferdsel' AND arealdekke <> 'Ferskvann_elv_bekk' AND arealdekke <> 'Ferskvann_kanal' AND arealdekke <> 'Ferskvann_innsjo_tjern_regulert' AND arealdekke <> 'Ferskvann_innsjo_tjern' AND isoperimetric_quotient < 0.3"
        )
        arcpy.analysis.Buffer(
            in_features=layer,
            out_feature_class=self.files["eliminate_selected_negative_buffers"],
            buffer_distance_or_field="-4 Meters",
        )
        arcpy.analysis.Buffer(
            in_features=self.files["eliminate_selected_negative_buffers"],
            out_feature_class=self.files["eliminate_selected_positive_buffers"],
            buffer_distance_or_field="4 Meters",
        )

    @timing_decorator
    def clip_and_erase(self):
        arcpy.analysis.Clip(
            in_features=self.files["eliminate_after_elim"],
            clip_features=self.files["eliminate_selected_positive_buffers"],
            out_feature_class=self.files["eliminate_clipped"]
        )
        arcpy.analysis.Erase(
            in_features=self.files["eliminate_after_elim"],
            erase_features=self.files["eliminate_selected_positive_buffers"],
            out_feature_class=self.files["eliminate_erased"]
        )

        arcpy.management.MultipartToSinglepart(
            in_features=self.files["eliminate_erased"],
            out_feature_class=self.files["eliminate_erased_singlepart"]
        )

        arcpy.management.MultipartToSinglepart(
            in_features=self.files["eliminate_clipped"],
            out_feature_class=self.files["eliminate_clipped_singlepart"]
        )

        arcpy.management.Merge(
            inputs=[self.files["eliminate_clipped_singlepart"], self.files["eliminate_erased_singlepart"]],
            output=self.files["eliminate_merged_clipped_erased"],
        )

        self.add_fields(self.files["eliminate_merged_clipped_erased"])

        print("Repairing geometry...")
        arcpy.management.RepairGeometry(
            in_features=self.files["eliminate_merged_clipped_erased"],
            delete_null="DELETE_NULL",
            validation_method="ESRI"
        )
        print("Geometry repaired.")

        layer = "eliminate_merged_clipped_erased_layer"
        arcpy.management.MakeFeatureLayer(
            in_features=self.files["eliminate_merged_clipped_erased"],
            out_layer=layer,
            where_clause="area < 100 AND arealdekke <> 'Samferdsel' AND arealdekke <> 'Ferskvann_elv_bekk' AND arealdekke <> 'Ferskvann_kanal' AND arealdekke <> 'Ferskvann_innsjo_tjern_regulert' AND arealdekke <> 'Ferskvann_innsjo_tjern'"
        )
    
        arcpy.management.Eliminate(
            in_features=layer,
            out_feature_class=self.files["eliminate_clip_erase_eliminated"],
            selection="LENGTH",
        )

    @timing_decorator
    def integrate(self):
        arcpy.management.Integrate(
            in_features=self.files["eliminate_final_elim"],
            cluster_tolerance="0.09 Meters",
        )

    @timing_decorator
    def run(self):
        environment_setup.main()
        self.fetch_data()
        self.add_fields(self.files["eliminate_input"])
        self.eliminate(self.files["eliminate_input"], self.files["eliminate_after_elim"])
        self.buffer_potential_spikes()
        self.clip_and_erase()
        self.eliminate(self.files["eliminate_clip_erase_eliminated"], self.files["eliminate_final_elim"])

        self.integrate()

        arcpy.management.CopyFeatures(
            in_features=self.files["eliminate_final_elim"],
            out_feature_class=self.output_feature
        )

def eliminate_normal_call():

    eliminate_config = logic_config.EliminateSmallPolygonsInitKwargs(
        input_feature=Arealdekke_N10.dissolve_arealdekke.value,
        output_feature=Arealdekke_N10.elim_output.value,
        work_file_manager_config=core_config.WorkFileConfig(
            root_file=Arealdekke_N10.dissolve_arealdekke_root.value
        ),
    )
    EliminateSmallPolygons(eliminate_small_polygons_config=eliminate_config).run()


def partition_call_eliminate(input_file, output_file):
    eliminate = "eliminate"
    elim_small_polygon = "elim_small_polygon"
    partition_input_config = core_config.PartitionInputConfig(
        entries=[
            core_config.InputEntry.processing_input(
                object=eliminate,
                path=input_file,
            )
        ]
    )

    partition_output_config = core_config.PartitionOutputConfig(
        entries=[
            core_config.OutputEntry.vector_output(
                object=eliminate,
                tag=elim_small_polygon,
                path=output_file,
            )
        ]
    )

    partiton_area_io_config = core_config.PartitionIOConfig(
        input_config=partition_input_config,
        output_config=partition_output_config,
        documentation_directory=Arealdekke_N10.elim_documentation.value,
    )

    # Method Config:

    partiton_input = core_config.InjectIO(object=eliminate, tag="input")
    partition_output = core_config.InjectIO(object=eliminate, tag=elim_small_polygon)

    elim_init_config = logic_config.EliminateSmallPolygonsInitKwargs(
        input_feature=partiton_input,
        output_feature=partition_output,
        work_file_manager_config=core_config.WorkFileConfig(
            root_file=Arealdekke_N10.elim_root.value
        ),
    )
    elim_method = core_config.ClassMethodEntryConfig(
        class_=EliminateSmallPolygons,
        method=EliminateSmallPolygons.run,
        init_params=elim_init_config,
    )
    partition_method_config = core_config.MethodEntriesConfig(
        entries=[elim_method]
    )

    # Run Config:
    partiton_run_config = core_config.PartitionRunConfig(
        max_elements_per_partition=50_000,
        context_radius_meters=0,
        run_partition_optimization=False,
    )

    # WorkFileConfig:
    partiton_workfile_config = core_config.WorkFileConfig(
        root_file=Arealdekke_N10.elim_root.value
    )

    # PartitionIterator Config:
    partition_elim = PartitionIterator(
        partition_io_config=partiton_area_io_config,
        partition_method_inject_config=partition_method_config,
        partition_iterator_run_config=partiton_run_config,
        work_file_manager_config=partiton_workfile_config,
    )

    partition_elim.run()    


if __name__ == "__main__":
    #normal_call()
    #partition_call()
    #eliminate_normal_call()
    partition_call_eliminate(Arealdekke_N10.dissolve_arealdekke.value, Arealdekke_N10.elim_output.value)
    #partition_call_gangsykkel(Arealdekke_N10.dissolve_arealdekke_w_iq.value, Arealdekke_N10.dissolve_gangsykkel.value)
    #partition_call_gangsykkel(Arealdekke_N10.dissolve_gangsykkel.value, Arealdekke_N10.dissolve_gangsykkel2.value)
    #partition_call_gangsykkel(Arealdekke_N10.dissolve_gangsykkel2.value, Arealdekke_N10.dissolve_gangsykkel3.value)
    
