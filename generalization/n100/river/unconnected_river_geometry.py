import arcpy
import multiprocessing
from multiprocessing import Pool, Manager
from tqdm import tqdm

import config
from env_setup import environment_setup
from input_data import input_n50
from input_data import input_n100
from custom_tools import custom_arcpy
from file_manager.n100.file_manager_rivers import River_N100


def main():
    geomotry_search_tolerance = 30
    id_field = "orig_ob_id"
    cpu_usage_percentage = 0.9
    num_cores = int(multiprocessing.cpu_count() * cpu_usage_percentage)
    setup_arcpy_environment()
    copy_input_features(geomotry_search_tolerance)

    # Feature classes
    buffer_fc = River_N100.unconnected_river_geometry__river_dangles_buffer__n100.value
    line_fc = River_N100.unconnected_river_geometry__unsplit_river_features__n100.value
    polygon_fc = (
        River_N100.unconnected_river_geometry__water_area_features_selected__n100.value
    )
    point_fc = River_N100.unconnected_river_geometry__river_dangles__n100.value

    # Determine total number of buffers
    total_buffers = int(arcpy.GetCount_management(buffer_fc)[0])

    # Define the percentage of the dataset to process in each batch (e.g., 25%)
    batch_percentage = 0.05
    batch_size = int(total_buffers * batch_percentage)

    # Prepare arguments for each batch
    batch_args = [
        (
            start,
            min(start + batch_size, total_buffers),
            line_fc,
            polygon_fc,
            buffer_fc,
            id_field,
        )
        for start in range(0, total_buffers, batch_size)
    ]

    with Manager() as manager:
        shared_results = manager.list()  # Shared list for results
        queue = manager.Queue()  # Manager Queue for progress tracking

        # Include both shared_results and queue in the tuples
        args_with_shared_results = [(*arg, shared_results, queue) for arg in batch_args]

        with Pool(processes=num_cores) as pool:
            pool.starmap(process_batch, args_with_shared_results)

        all_problematic_ids = list(shared_results)
        print("All problematic IDs:", all_problematic_ids)

    try:
        resolve_geometry(id_field, all_problematic_ids)
    except Exception as e:
        print("Error in resolve_geometry:", e)


def setup_arcpy_environment():
    """
    Summary:
        Sets up the ArcPy environment based on predefined settings defined in `general_setup`.
        This function ensures that the ArcPy environment is properly configured for the specific project by utilizing
        the `general_setup` function from the `environment_setup` module.

    Details:
        - It calls the `general_setup` function from the `environment_setup` module to set up the ArcPy environment based on predefined settings.
    """
    environment_setup.general_setup()


def copy_input_features(geomotry_search_tolerance):
    arcpy.UnsplitLine_management(
        in_features=config.river_sprint_feature,
        out_feature_class=River_N100.unconnected_river_geometry__unsplit_river_features__n100.value,
    )

    print(
        f"Created {River_N100.unconnected_river_geometry__unsplit_river_features__n100.value}"
    )

    id_field = "orig_ob_id"
    # Adding transferring the NBR value to the matrikkel_bygningspunkt
    arcpy.AddField_management(
        in_table=River_N100.unconnected_river_geometry__unsplit_river_features__n100.value,
        field_name=id_field,
        field_type="LONG",
    )
    arcpy.CalculateField_management(
        in_table=River_N100.unconnected_river_geometry__unsplit_river_features__n100.value,
        field=id_field,
        expression="!OBJECTID!",
    )
    print(f"Added field orig_ob_id")

    sql_expression_water_features = f"OBJTYPE = 'FerskvannTørrfall' Or OBJTYPE = 'Innsjø' Or OBJTYPE = 'InnsjøRegulert' Or OBJTYPE = 'Havflate' Or OBJTYPE = 'ElvBekk'"
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n50.ArealdekkeFlate,
        expression=sql_expression_water_features,
        output_name=River_N100.unconnected_river_geometry__water_area_features__n100.value,
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=River_N100.unconnected_river_geometry__water_area_features__n100.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE.value,
        select_features=River_N100.unconnected_river_geometry__unsplit_river_features__n100.value,
        output_name=River_N100.unconnected_river_geometry__water_area_features_selected__n100.value,
        search_distance=f"{geomotry_search_tolerance} Meters",
    )

    arcpy.management.FeatureVerticesToPoints(
        in_features=River_N100.unconnected_river_geometry__unsplit_river_features__n100.value,
        out_feature_class=River_N100.unconnected_river_geometry__river_dangles__n100.value,
        point_location="DANGLE",
    )
    print(f"Created {River_N100.unconnected_river_geometry__river_dangles__n100.value}")

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=River_N100.unconnected_river_geometry__river_dangles__n100.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT.value,
        select_features=River_N100.unconnected_river_geometry__water_area_features_selected__n100.value,
        output_name=River_N100.unconnected_river_selected_river_dangles__n100.value,
        inverted=True,
    )

    arcpy.analysis.PairwiseBuffer(
        in_features=River_N100.unconnected_river_selected_river_dangles__n100.value,
        out_feature_class=River_N100.unconnected_river_geometry__river_dangles_buffer__n100.value,
        buffer_distance_or_field=f"{geomotry_search_tolerance} Meters",
    )
    print(
        f"Created {River_N100.unconnected_river_geometry__river_dangles_buffer__n100.value}"
    )

    # Feature classes
    buffer_fc = River_N100.unconnected_river_geometry__river_dangles_buffer__n100.value
    line_fc = River_N100.unconnected_river_geometry__unsplit_river_features__n100.value
    polygon_fc = (
        River_N100.unconnected_river_geometry__water_area_features_selected__n100.value
    )
    point_fc = River_N100.unconnected_river_selected_river_dangles__n100.value


def process_batch(
    start,
    end,
    line_fc,
    polygon_fc,
    buffer_fc,
    id_field,
    shared_results,
    queue,
):
    lines = [
        (row[0], row[1]) for row in arcpy.da.SearchCursor(line_fc, [id_field, "SHAPE@"])
    ]
    polygons = [row[0] for row in arcpy.da.SearchCursor(polygon_fc, ["SHAPE@"])]

    query = f"OBJECTID >= {start} AND OBJECTID < {end}"
    with arcpy.da.SearchCursor(
        buffer_fc, [id_field, "SHAPE@"], where_clause=query
    ) as buffer_cursor:
        for buffer_row in buffer_cursor:
            buffer_id, buffer_geom = buffer_row

            line_intersect = any(
                line_id != buffer_id
                and (
                    not buffer_geom.disjoint(line_geom)
                    or buffer_geom.touches(line_geom)
                )
                for line_id, line_geom in lines
            )

            polygon_intersect = any(
                not buffer_geom.disjoint(poly_geom) or buffer_geom.touches(poly_geom)
                for poly_geom in polygons
            )

            if line_intersect or polygon_intersect:
                shared_results.append(buffer_id)  # Directly append to the shared list

    queue.put(1)


def resolve_geometry(
    id_field,
    all_problematic_ids,
):
    # Check if the list is empty
    if not all_problematic_ids:
        print("No problematic IDs found.")
        return

    # Convert list of IDs to a comma-separated string
    ids_string = ", ".join(map(str, all_problematic_ids))
    print("SQL Query String:", ids_string)

    # Construct the SQL query
    sql_problematic_ids = f"{id_field} IN ({ids_string})"
    print("SQL Query:", sql_problematic_ids)

    # Proceed with the selection and creation of features
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=River_N100.unconnected_river_geometry__unsplit_river_features__n100.value,
        expression=sql_problematic_ids,
        output_name=River_N100.unconnected_river_geometry__problematic_river_lines__n100.value,
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=River_N100.unconnected_river_geometry__river_dangles__n100.value,
        expression=sql_problematic_ids,
        output_name=River_N100.unconnected_river_geometry__problematic_river_dangles__n100.value,
    )


if __name__ == "__main__":
    main()
