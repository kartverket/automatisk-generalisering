from file_manager.n100.file_manager_buildings import Building_N100
from custom_tools.polygon_processor import PolygonProcessor

building_symbol_dimensions = {
    1: (145, 145),
    2: (145, 145),
    3: (195, 145),
    4: (40, 40),
    5: (80, 80),
    6: (30, 30),
    7: (45, 45),
    8: (45, 45),
    9: (53, 45),
}

polygon_processor = PolygonProcessor(
    input_building_points=Building_N100.building_point_buffer_displacement__displaced_building_points__n100.value,
    output_polygon_feature_class=Building_N100.points_to_polygon__transform_points_to_square_polygons__n100.value,
    building_symbol_dimensions=building_symbol_dimensions,
    symbol_field_name="symbol_val",
    index_field_name="OBJECTID",
)


if __name__ == "__main__":
    polygon_processor.run()
