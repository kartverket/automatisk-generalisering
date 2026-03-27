# Arealdekke
    This folder contains all functions and classes that are specific to the arealdekke generalization pipeline

# Structure
    arealdekke_orchestrator.py is the main file that imports and calls the different functions and classes in order.
    It should only contain calls of the functions/classes, 
    all set up like partition iterator or parameters except input and output files should be handled in the file containing the class/function 
    Parameters that are map scale specific or general rules for the class/function should be defined in parameters.yml,

# Functions/Classes
    attribute_changer.py:
        Categorizes arealdekke based on hovedklasse, underklasse and grunnforhold

    arealdekke_dissolver.py: 
        Main dissolve class that dissolves based on the categories set up in attribute_changer.py
        Contains function restore_data_polygon_without_feature_to_point, this function will follow the rules for restoring data after dissolving and can be used by other functions/classes  
    
    eliminate_small_polygons.py:
        Eliminates too small polygons based on area times isoperimetric quotient and removes narrow polygon parts using minus buffer,
        Contains function Eliminate_holes that can be useful for other classes to call. this function finds holes in the chosen polygons and eliminate the polygons in those holes if they are within rules set in parameters.yml for Eliminate class.
    
    gangsykkel_dissolver.py:
        Dissolves GangSykkelVeg into roads if they are adjacent, calls eliminate_holes for samferdsel(without gangvei) afterwards
        
    buff_small_polygon_segments.py:
        Function that buffs polygon segments under a minimum with requirement without overlapping locked features.  Uses area_merger.py afterwards to put the
        new enlarged areas back into the arealdekke.



