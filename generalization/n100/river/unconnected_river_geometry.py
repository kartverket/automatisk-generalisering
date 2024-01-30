import arcpy
import multiprocessing
from multiprocessing import Pool
from tqdm import tqdm

import config
from env_setup import environment_setup
from input_data import input_n50
from input_data import input_n100
from custom_tools import custom_arcpy
from file_manager.n100.file_manager_rivers import River_N100
from custom_tools.polygon_processor import PolygonProcessor


def main():
    geomotry_search_tolerance = 30
    id_field = "orig_ob_id"
    cpu_usage_percentage = 1
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
    batch_percentage = 0.25
    batch_size = int(total_buffers * batch_percentage)

    # Prepare arguments for each batch
    batch_args = [
        (
            start,
            min(start + batch_size, total_buffers),
            line_fc,
            polygon_fc,
            point_fc,
            buffer_fc,
            id_field,
            geomotry_search_tolerance,
        )
        for start in range(0, total_buffers, batch_size)
    ]

    # Use multiprocessing Pool to process each batch in parallel
    with Pool(processes=num_cores) as pool:
        results = pool.starmap(process_batch, batch_args)

    # Combine results from all batches
    all_problematic_ids = [item for sublist in results for item in sublist]


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

    arcpy.analysis.PairwiseBuffer(
        in_features=River_N100.unconnected_river_geometry__river_dangles__n100.value,
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
    point_fc = River_N100.unconnected_river_geometry__river_dangles__n100.value


def process_batch(
    start,
    end,
    line_fc,
    polygon_fc,
    point_fc,
    buffer_fc,
    id_field,
    geomotry_search_tolerance,
):
    # List to store buffer IDs for this batch
    problematic_ids = []

    # Ensure id_field is correctly used in arcpy.da.SearchCursor
    if not isinstance(id_field, str):
        raise ValueError("id_field must be a string")

    lines = [
        (row[0], row[1]) for row in arcpy.da.SearchCursor(line_fc, [id_field, "SHAPE@"])
    ]
    polygons = [row[0] for row in arcpy.da.SearchCursor(polygon_fc, ["SHAPE@"])]

    # Create a SQL query to select a batch of buffers
    query = f"OBJECTID >= {start} AND OBJECTID < {end}"

    with arcpy.da.SearchCursor(
        buffer_fc, [id_field, "SHAPE@"], where_clause=query
    ) as buffer_cursor:
        for buffer_row in buffer_cursor:
            buffer_id, buffer_geom = buffer_row
            point_intersects = False

            # Check for corresponding point intersecting with any line (not same ID) or polygon
            with arcpy.da.SearchCursor(point_fc, [id_field, "SHAPE@"]) as point_cursor:
                for point_row in point_cursor:
                    point_id, point_geom = point_row

                    if point_id == buffer_id:
                        line_intersect = any(
                            line_id != point_id
                            and (
                                not point_geom.disjoint(line_geom)
                                or point_geom.touches(line_geom)
                            )
                            for line_id, line_geom in lines
                        )
                        polygon_intersect = any(
                            not point_geom.disjoint(poly_geom)
                            or point_geom.touches(poly_geom)
                            for poly_geom in polygons
                        )

                        if line_intersect or polygon_intersect:
                            point_intersects = True
                            break

            if point_intersects:
                continue  # Skip to the next buffer if any point intersects

            # Check against lines and polygons if no point intersection found
            buffer_intersects = any(
                line_id != buffer_id
                and (
                    not buffer_geom.disjoint(line_geom)
                    or buffer_geom.touches(line_geom)
                )
                for line_id, line_geom in lines
            ) or any(
                not buffer_geom.disjoint(poly_geom) or buffer_geom.touches(poly_geom)
                for poly_geom in polygons
            )

            # Add buffer ID if it meets all criteria
            if buffer_intersects:
                problematic_ids.append(buffer_id)
                print(f"all conditions met for {buffer_id}")
    return problematic_ids


if __name__ == "__main__":
    main()
