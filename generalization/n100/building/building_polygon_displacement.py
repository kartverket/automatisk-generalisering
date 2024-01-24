# Importing modules
import numpy as np
import arcpy
import os

# Importing custom modules
import config
from input_data import input_n100
from custom_tools import custom_arcpy

# Importing environment settings
from env_setup import environment_setup

environment_setup.general_setup()

# Importing file manager
from file_manager.n100.file_manager_buildings import Building_N100


def main():
    """
    replace with docstring
    """
    # propagate_displacement_building_polygons()
    # features_500_m_from_building_polygons()
    # apply_symbology_to_layers()
    # rbc_selection()
    resolve_building_conflict_building_polygon()
    # creating_road_buffer()
    # erasing_building_polygons_with_road_buffer()
    # small_building_polygons_to_point()


def propagate_displacement_building_polygons():
    """
    replace with docstring
    """
    print("Propogate displacement ...")
    # Copying layer so no changes are made to the original
    arcpy.management.Copy(
        in_data=Building_N100.simplify_building_polygons__simplified_grunnriss__n100.value,
        out_data=Building_N100.propagate_displacement_building_polygons__building_polygon_pre_propogate_displacement__n100.value,
    )

    # Selecting propogate displacement features 500 meter from building polgyons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=config.displacement_feature,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.propagate_displacement_building_polygons__building_polygon_pre_propogate_displacement__n100.value,
        output_name=Building_N100.propagate_displacement_building_polygons__displacement_feature_1000_m_from_building_polygon__n100.value,
        search_distance="1000 Meters",
    )

    # Running propogate displacement for building polygons
    arcpy.cartography.PropagateDisplacement(
        in_features=Building_N100.propagate_displacement_building_polygons__building_polygon_pre_propogate_displacement__n100.value,
        displacement_features=Building_N100.propagate_displacement_building_polygons__displacement_feature_1000_m_from_building_polygon__n100.value,
        adjustment_style="SOLID",
    )

    # Copying and assigning new name to layer
    arcpy.management.Copy(
        in_data=Building_N100.propagate_displacement_building_polygons__building_polygon_pre_propogate_displacement__n100.value,
        out_data=Building_N100.propagate_displacement_building_polygons__after_propogate_displacement__n100.value,
    )


def features_500_m_from_building_polygons():
    """
    replace with docstring
    """
    print("Selecting features 500 meter from building polygon ...")
    # Selecting begrensningskurve 500 meters from building polygons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.preparation_begrensningskurve__selected_waterfeatures_from_begrensningskurve__n100.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.propagate_displacement_building_polygons__after_propogate_displacement__n100.value,
        output_name=Building_N100.features_500_m_from_building_polygons__selected_begrensningskurve__n100.value,
        search_distance="500 Meters",
    )

    # Selecting roads 500 meters from building polygons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.preperation_veg_sti__unsplit_veg_sti__n100.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.simplify_building_polygons__simplified_grunnriss__n100.value,
        output_name=Building_N100.features_500_m_from_building_polygons__selected_roads__n100.value,
        search_distance="500 Meters",
    )


def rbc_selection():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.AdminFlate,
        expression="NAVN = 'Asker'",
        output_name=Building_N100.rbc_selection__selection_area_resolve_building_conflicts__n100.value,
    )

    # List of dictionaries containing parameters for each selection
    selections = [
        {
            "input_layer": Building_N100.propagate_displacement_building_polygons__after_propogate_displacement__n100.value,
            "output_name": Building_N100.rbc_selection__grunnriss_selection_rbc__n100.value,
        },
        {
            "input_layer": Building_N100.features_500_m_from_building_polygons__selected_roads__n100.value,
            "output_name": Building_N100.rbc_selection__veg_sti_selection_rbc_rbc__n100.value,
        },
        {
            "input_layer": Building_N100.features_500_m_from_building_polygons__selected_begrensningskurve__n100.value,
            "output_name": Building_N100.rbc_selection__begrensningskurve_selection_rbc__n100.value,
        },
    ]

    # Loop over the selections and apply the function
    for selection in selections:
        custom_arcpy.select_location_and_make_permanent_feature(
            input_layer=selection["input_layer"],
            overlap_type=custom_arcpy.OverlapType.INTERSECT,
            select_features=Building_N100.rbc_selection__selection_area_resolve_building_conflicts__n100.value,
            output_name=selection["output_name"],
        )


""""
def apply_symbology_to_layers():
    print("Applying symbology ...")
    # Applying symbology to building polygons
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.propagate_displacement_building_polygons__after_propogate_displacement__n100.value,
        in_symbology_layer=config.symbology_n100_grunnriss,
        output_name=Building_N100.apply_symbology_to_layers__building_polygon__n100__lyrx.value,
    )
    # Applying symbology to roads
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.features_500_m_from_building_polygons__selected_roads__n100.value,
        in_symbology_layer=config.symbology_n100_veg_sti,
        output_name=Building_N100.apply_symbology_to_layers__roads__n100__lyrx.value,
    )

    # Applying symbology to begrensningskurve (limiting curve)
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.preparation_begrensningskurve__begrensningskurve_buffer_erase_2__n100.value,
        in_symbology_layer=config.symbology_n100_begrensningskurve,
        output_name=Building_N100.apply_symbology_to_layers__begrensningskurve__n100__lyrx.value,
    )

    """


def apply_symbology_to_layers():
    """
    replace with docstring
    """
    print("Applying symbology ...")
    # Applying symbology to building polygons
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.rbc_selection__grunnriss_selection_rbc__n100.value,
        in_symbology_layer=config.symbology_n100_grunnriss,
        output_name=Building_N100.apply_symbology_to_layers__building_polygon__n100__lyrx.value,
    )
    # Applying symbology to roads
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.rbc_selection__veg_sti_selection_rbc_rbc__n100.value,
        in_symbology_layer=config.symbology_n100_veg_sti,
        output_name=Building_N100.apply_symbology_to_layers__roads__n100__lyrx.value,
    )

    # Applying symbology to begrensningskurve (limiting curve)
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.rbc_selection__begrensningskurve_selection_rbc__n100.value,
        in_symbology_layer=config.symbology_n100_begrensningskurve,
        output_name=Building_N100.apply_symbology_to_layers__begrensningskurve__n100__lyrx.value,
    )


def resolve_building_conflict_building_polygon():
    """
    replace with docstring
    """
    print("Resolving building conflicts ...")
    # Setting scale to 1: 100 000
    arcpy.env.referenceScale = "100000"

    test_barriers = (
        [
            Building_N100.apply_symbology_to_layers__roads__n100__lyrx.value,
            "false",
            "15 meters",
        ],
    )

    # Resolve Building Polygon with roads and begrensningskurve as barriers
    arcpy.cartography.ResolveBuildingConflicts(
        in_buildings=Building_N100.apply_symbology_to_layers__building_polygon__n100__lyrx.value,
        invisibility_field="invisibility",
        in_barriers=test_barriers,
        building_gap="30 meters",
        minimum_size="1 meters",
    )

    print("Finished")


def creating_road_buffer():
    """
    replace with docstring
    """

    print("Creating road buffers ...")
    # Dictionary with SQL queries and their corresponding buffer widths
    sql_queries = {
        "MOTORVEGTYPE = 'Motorveg'": 42.5,
        """ 
        SUBTYPEKODE = 3 
        Or MOTORVEGTYPE = 'Motortrafikkveg' 
        Or (SUBTYPEKODE = 2 And MOTORVEGTYPE = 'Motortrafikkveg') 
        Or (SUBTYPEKODE = 2 And MOTORVEGTYPE = 'Ikke motorveg') 
        Or (SUBTYPEKODE = 4 And MOTORVEGTYPE = 'Ikke motorveg') 
        """: 22.5,
        """
        SUBTYPEKODE = 1
        Or SUBTYPEKODE = 5
        Or SUBTYPEKODE = 6
        Or SUBTYPEKODE = 9
        """: 20,
        """
        SUBTYPEKODE = 7
        Or SUBTYPEKODE = 8
        Or SUBTYPEKODE = 10
        Or SUBTYPEKODE =11
        """: 7.5,
    }

    selection_name_base = Building_N100.creating_road_buffer__selection__n100.value
    buffer_name_base = Building_N100.creating_road_buffer__buffers__n100.value

    # List to store the road buffer outputs
    road_buffer_output_names = []

    # Counter for naming the individual road type selections
    counter = 1

    # Loop through the dictionary (Key: SQL query and Value: width) to create buffers around the different roads
    for sql_query, original_width in sql_queries.items():
        selection_output_name = f"{selection_name_base}_{counter}"
        buffer_width = original_width + 15
        buffer_output_name = f"{buffer_name_base}_{buffer_width}m_{counter}"

        # Selecting road types and making new feature layer based on SQL query
        custom_arcpy.select_attribute_and_make_feature_layer(
            input_layer=Building_N100.preperation_veg_sti__unsplit_veg_sti__n100.value,
            expression=sql_query,
            output_name=selection_output_name,
        )

        # Making a buffer around each road type with specified width + 15 meters
        arcpy.analysis.PairwiseBuffer(
            in_features=selection_output_name,
            out_feature_class=buffer_output_name,
            buffer_distance_or_field=f"{buffer_width} Meters",
        )

        # Add buffer output names to list
        road_buffer_output_names.append(buffer_output_name)
        # Increase the counter by 1
        counter += 1

    # Merge all buffers into a single feature class
    arcpy.management.Merge(
        inputs=road_buffer_output_names,
        output=Building_N100.creating_road_buffer__merged_road_buffers__n100.value,
    )


def erasing_building_polygons_with_road_buffer():
    """
    replace with docstring
    """

    print("Erasing building polygons with road buffer ...")
    # Erasing building polygons with buffer
    arcpy.analysis.Erase(
        in_features=Building_N100.propagate_displacement_building_polygons__after_propogate_displacement__n100.value,
        erase_features=Building_N100.creating_road_buffer__merged_road_buffers__n100.value,
        out_feature_class=Building_N100.erasing_building_polygons_with_road_buffer__erased_buildings__n100.value,
    )

    # Multipart to singlepart to separate split parts of the building
    arcpy.management.MultipartToSinglepart(
        in_features=Building_N100.erasing_building_polygons_with_road_buffer__erased_buildings__n100.value,
        out_feature_class=Building_N100.erasing_building_polygons_with_road_buffer__after_multipart_to_singlepart__n100.value,
    )

    # Create a dictionary to store the OBJECT_ID of the feature with the largest Shape_area for each ORIG_FID
    largest_object_ids = {}

    # Iterate through the features and store the OBJECT_ID of the largest Shape_area for each ORIG_FID
    with arcpy.da.SearchCursor(
        Building_N100.erasing_building_polygons_with_road_buffer__after_multipart_to_singlepart__n100.value,
        ["ORIG_FID", "OBJECTID", "Shape_Area"],
    ) as cursor:
        for row in cursor:
            orig_fid, object_id, shape_area = row
            if (
                orig_fid not in largest_object_ids
                or shape_area > largest_object_ids[orig_fid][1]
            ):
                largest_object_ids[orig_fid] = (object_id, shape_area)

    # Create a list of OBJECTIDs for the features with the largest Shape_Area
    selected_object_ids = [record[0] for record in largest_object_ids.values()]

    # Construct the SQL query using the list of OBJECTIDs
    selected_object_ids_query = (
        f"OBJECTID IN ({', '.join(map(str, selected_object_ids))})"
    )

    # Keeping all building parts with biggest Shape_Area
    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=Building_N100.erasing_building_polygons_with_road_buffer__after_multipart_to_singlepart__n100.value,
        expression=selected_object_ids_query,
        output_name=Building_N100.erasing_building_polygons_with_road_buffer__selected_building_parts__n100.value,
    )

    # Selecting buildings that are no longer going to be included
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.erasing_building_polygons_with_road_buffer__erased_buildings__n100.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.erasing_building_polygons_with_road_buffer__selected_building_parts__n100.value,
        output_name=Building_N100.erasing_building_polygons_with_road_buffer__building_polygons_erased_and_reduced__n100.value,
        inverted=True,
    )
    print("Merging polygons layers ...")
    # Merging building parts and
    arcpy.management.Merge(
        inputs=[
            Building_N100.erasing_building_polygons_with_road_buffer__selected_building_parts__n100.value,
            Building_N100.erasing_building_polygons_with_road_buffer__building_polygons_erased_and_reduced__n100.value,
        ],
        output=Building_N100.erasing_building_polygons_with_road_buffer__reduced_building_polygons__n100.value,
    )

    # Selecting building polygons that are to kept as polygons
    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=Building_N100.erasing_building_polygons_with_road_buffer__reduced_building_polygons__n100.value,
        expression="Shape_Area >= 3200",
        output_name=Building_N100.erasing_building_polygons_with_road_buffer__building_polygons_erased_final__n100.value,
    )


def small_building_polygons_to_point():
    """
    replace with docstring
    """
    print("Transforming small polygons to points ...")
    # Selecting building polygons that are too small
    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=Building_N100.erasing_building_polygons_with_road_buffer__reduced_building_polygons__n100.value,
        expression="Shape_Area < 3200",
        output_name=Building_N100.small_building_polygons_to_point__building_polygons_too_small__n100.value,
    )

    # Polygon to point
    arcpy.management.FeatureToPoint(
        in_features=Building_N100.small_building_polygons_to_point__building_polygons_too_small__n100.value,
        out_feature_class=Building_N100.small_building_polygons_to_point__building_points__n100.value,
    )

    print("Script finished.")


if __name__ == "__main__":
    main()
