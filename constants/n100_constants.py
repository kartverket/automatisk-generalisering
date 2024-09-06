from enum import Enum
from typing import Union


class N100_Values(Enum):
    # Building constants
    buffer_clearance_distance_m: int = 45
    rbc_barrier_clearance_distance_m: int = 30
    rbc_building_clearance_distance_m: int = 30
    # Simplify building polygon constants
    minimum_selection_building_polygon_size_m2: int = 2500
    minimum_simplified_building_polygon_size_m2: int = 3200
    simplify_building_tolerance_m: int = 75
    simplify_polygon_tolerance_m: int = 15
    building_polygon_aggregation_distance_m: int = 4

    building_water_intrusion_distance_m: int = 15


class N100_Symbology(Enum):
    building_symbol_dimensions = {
        1: (175, 175),  # Hospital
        2: (175, 175),  # Hospital
        3: (160, 120),  # Church
        4: (100, 100),
        5: (45, 45),
        6: (45, 45),
        7: (45, 45),
        8: (45, 45),
        9: (65, 55),
        10: (130, 130),  # Railway station
        11: (130, 130),  # Tourist Cabin
    }


class N100_SQLResources(Enum):
    nbr_symbol_val_code_block = (
        "def determineVal(nbr):\n"
        "    if nbr == 970:\n"
        "        return 1\n"  # Red Hospital
        "    elif nbr == 719:\n"
        "        return 2\n"  # Green Hospital
        "    elif nbr == 671:\n"
        "        return 3\n"  # Church
        "    elif nbr in [113,123,124,163]:\n"
        "        return 4\n"  # Farms
        "    elif nbr in [111,112,121,122,131,133,135,136,141,142,143,144,145,146,159,161,162,171,199,524]:\n"
        "        return 5\n"  # Small white squares
        "    elif nbr in [151,152,211,212,214,221,231,232,233,243,244,311,312,313,321,322,323,330,411,412,415,416,4131,441,521,522,523,529,532,621,641,642,643,651,652,653,661,662,672,673,674,675,731,821,822,319,329,449,219,659,239,439,223,611,649,229,419,429,623,655,664,679,824]:\n"
        "        return 6\n"  # Small black squares
        "    elif nbr in [531,612,613,614,615,616,619,629,819,829,669,533,539]:\n"
        "        return 7\n"  # Small purple squares
        "    elif nbr in [721,722,723,732,739,729]:\n"
        "        return 8\n"  # Small green squares
        "    elif nbr in [172,181,182,183,193,216,241,245,248,654,999,249,840]:\n"
        "        return 9\n"  # Black triangles
        "    elif nbr in [956]:\n"
        "        return 11\n"  # Tourist Cabin
        "    else:\n"
        "        return -99\n"
    )

    symbol_val_to_hierarchy = """def determineHierarchy(symbol_val):\n
        if symbol_val in [1, 2, 3, 11]:\n
            return 1\n
        elif symbol_val == 4:\n
            return 2\n
        else:\n
            return 3\n"""

    nbr_to_hierarchy_overlapping_points = (
        "def determineHierarchy(nbr):\n"
        "    if nbr == 970:\n"
        "        return 1\n"  # Red Hospital
        "    elif nbr == 671:\n"
        "        return 2\n"  # Church
        "    elif nbr == 719:\n"
        "        return 3\n"  # Green Hospital
        "    elif nbr == 956:\n"
        "        return 4\n"  # Tourist Cabin
        "    elif nbr in [113,123,124,163]:\n"
        "        return 5\n"  # Farms
        "    elif nbr in [111,112,121,122,131,133,135,136,141,142,143,144,145,146,159,161,162,171,199,524]:\n"
        "        return 6\n"
        "    elif nbr in [151,152,211,212,214,221,231,232,233,243,244,311,312,313,321,322,323,330,411,412,415,416,4131,441,521,522,523,529,532,621,641,642,643,651,652,653,661,662,672,673,674,675,731,821,822,319,329,449,219,659,239,439,223,611,649,229,419,429,623,655,664,679,824]:\n"
        "        return 7\n"
        "    elif nbr in [531,612,613,614,615,616,619,629,819,829,669,533,539]:\n"
        "        return 8\n"
        "    elif nbr in [721,722,723,732,739,729]:\n"
        "        return 9\n"
        "    elif nbr in [172,181,182,183,193,216,241,245,248,654,999,249,840]:\n"
        "        return 10\n"
        "    else:\n"
        "        return 10\n"
    )

    road_symbology_size_sql_selection = {
        "motorvegtype = 'Motorveg'": 43,
        """ 
        subtypekode = 3 
        Or motorvegtype = 'Motortrafikkveg' 
        Or (subtypekode = 2 And motorvegtype = 'Motortrafikkveg') 
        Or (subtypekode = 2 And motorvegtype = 'Ikke motorveg') 
        Or (subtypekode = 4 And motorvegtype = 'Ikke motorveg') 
        """: 23,
        """
        subtypekode = 1
        Or subtypekode = 5
        Or subtypekode = 6
        Or subtypekode = 9
        """: 20,
        """
        subtypekode = 7
        Or subtypekode = 8
        Or subtypekode = 10
        Or subtypekode =11
        """: 8,
    }

    urban_areas = "objtype = 'Tettbebyggelse' Or objtype = 'Industriområde' Or objtype = 'BymessigBebyggelse'"
