from enum import Enum

import config


# Defining universal paths for other files regardless of local path env_setup
class SymbologyN100(Enum):
    road = config.symbology_n100_roads
    road_buffer = config.symbology_n100_drawn_polygon
    begrensngings_kurve_buffer = config.symbology_n100_begrensningskurve_buffer
    begrensnings_kurve_line = config.symbology_n100_begrensningskurve_line
    begrensningskurve_polygon = config.symbology_n100_begrensningskurve_buffer
    building_point = config.symbology_n100_bygningspunkt
    building_polygon = config.symbology_n100_grunnriss
    squares = config.symbology_n100_drawn_polygon
    railway_station_squares = config.symbology_n100_railway_station_squares
    railway = config.symbology_n100_railway
