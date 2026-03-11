# Arealdekke
    This folder contains all functions and classes that are specific to the arealdekke generalization pipeline

# Structure
    arealdekke_orchestrator.py is the main file that imports and calls the different functions and classes in order.
    It should only contain calls of the functions/classes, 
    all set up like partition iterator or parameters except input and output files should be handled in the file containing the class/function 

# Functions/Classes
    attribute_changer.py:
        Categorizes arealdekke based on hovedklasse, underklasse and grunnforhold

    arealdekke_dissolver.py: 
        Main dissolve class that dissolves based on the categories set up in attribute_changer.py
    
    eliminate_small_polygons.py:
        Eliminates too small polygons based on area times isoperimetric quotient and removes narrow polygon parts using minus buffer, excluding rivers and samferdsel
    
    gangsykkel_dissolver.py:
        Dissolves GangSykkelVeg into roads if they are adjacent



