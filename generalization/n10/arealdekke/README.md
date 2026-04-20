# Arealdekke - Generalization Pipeline

This folder contains all functions and classes that are relevant and sepcific to the arealdekke generalization pipeline.

## 📁 Program Structure

The file structure of our arealdekke pipeline is structured around three core classes: **Arealdekke, Category and Program History**. Arealdekke represents the arealdekke as a whole. It is used to handle procedures where relations between the different arealdekke types matter. Category represents a single arealdekke type. This is used to process the arealdekke types seperately. Lastly, the Program History represents a yaml file that includes information about how far the program got during its last run. This ensures that the program can restart on its last checkpoint if the program suddenly stops.

The Python files is organized into the following folders:
````
root
|___generalization
    |___n10
        |___arealdekke
            |___Category_tools
            |___Orchestrator
            |___Parameters
            |___Overall_tools
````

***Category_tools***. Includes functionality used for editing single selections of land use categories.

***Orchestrator***. Contains the core classes and functions that constitutes the skeleton of the pipeline. Arealdekke_orchistrator.py is the pipeline root that initiates and calls all classes.

***Parameters***. Takes care of all parameters used to initialize classes and functionality based upon specific rule sets.

***Overall_tools***. Includes all functionality that handles arealdekke as one unit.
##
## Class documentation

### 🌻Arealdekke
- Parameters
    - self.wfm: WorkFileManager
    - self.files: Dictionary with the files used during the generalization of land use
    - self.preprocessed: Boolean telling if the preprocessing is finished or not
    - self.__map_scale
- Functions
    - Preprocess: Performes all the generalization not specific to a category to remove the vast amount of noise in the data set. Sets self.preprocessed = True when finished. This function uses the functions:
        - *Attribute_changer*
        - *Create_passability_layer*
        - *Arealdekke_dissolver*
        - *Island_controller*
        - *Eliminate_small_polygons*
        - *Gangsykkel_dissolver*
    - Add_categories: Adds relevant categories to be processed from a **.yml* file (*arealdekke_categories_config.yml*) with correct initialization
    - Process_categories: Performes all adjustment needed to generalize each category. Iterate through each category and their specific processing functions specified in the **.yml* file. The function starts by generalizing the specific category for itself, before the following functions are used to create a complete, final land use:
        - *Remove_overlaps*
        - *Fill_holes*
- Getters
    - Get_map_scale
    - Get_locked_categories
    - Get_category
- Setters
    - None

##
### 🌻Category_class.py

Main file for the *Category* class, including initialization function, processing functions of individually land use categories, and getters and setters.

- Parameters
    - self.__title: Category name
    - self.__operations: List of functions that should be applied to this specific category in the same order as in the list (can be an empty list)
    - self.__accessibility: Boolean telling whether or not this category is editable or not (finished processing)
    - self.__order
    - self.__map_scale
    - self.wfm: WorkFileManager
    - self.files: Dictionary with the files used during the generalization of each unique category
    - self.cat_tools: Dictionary with all possible functions that can be applied to a category
    - self.lyr: Feature layer for this category
- Functions
    - Process_category: Iterates through the list of operations (*self.__operations*) for this category and generalizes the geometries
    - `__str__`: Creates an informative string describing the category
- Getters
    - Get_title
    - Get_order
    - Get_accessibility
    - Get_operations
    - Get_map_scale
- Setters
    - Set_accessibility


##
### Additional Class Configuration

**Arealdekke_categories_config.yml**

Yaml file with setup for each unique land use category with descriptions of how to process the individual land use types. Each category contains:

- Title (category name)
- Operations (how the category should be processed)
- Accessibility (whether or not the layer is locked / finished processing)
- Order (processing rank / order)
- Map_scale

##
## 🧩 Category Tools

**Buff_small_polygon_segments.py**. Buffs polygon segments under a minimum width requirement without overlapping locked features. *Create_overlapping_land_use* can be used afterwards to merge the buffered segments back into the layer.

**Simplify_land_use.py**. Uses simplify and smooth to adjust polygons and remove small, extra details.



##
## Overall_tools

**Arealdekke_dissolver.py**. Main dissolve class that dissolves based on the categories defined in *attribute_changer.py*. This file contains:

- **Restore_data_polygon_without_feature_to_point**. This function follows the rules for restoring data after dissolving and can be used by other functions / classes.

**Attribute_analyzer.py**. File analyzing attribute data from csv file and list. Functions:
- Sort_results
- Write_to_file
- Load_rules

**Attribute_changer.py**

Re-categorizes *'arealdekke'* based on the fields:

- Arealdekke
- Hovedklasse
- Underklasse
- Grunnforhold

Field *'arealdekke'* is overwritten, and a new field *'gammel_arealdekke'* is added, along with the field *'fremkommelighet'*. This file contains:

- Attribute_changer

**Attribute_prioritizing.csv**

CSV file containing all the information of how to sort and reclassify the new *'arealdekke'* categories. The file contains the following columns:

- Arealdekke
- Hovedklasse
- Underklasse
- Grunnforhold
- Ny_arealdekke
- Fremkommelighet

**Eliminate_small_polygons.py**

Eliminates too small polygons based on *area times isoperimetric quotient* and removes narrow polygon parts using minus buffer. This file contains:

- Eliminate_holes

This function finds holes in the chosen polygons and eliminate those that are  within the specifications determined by the rule sets in parameters.yml for the *Eliminate class*. The function can be useful for other classes as well.

**Fill_holes.py**

Functionality to remove holes and replace it with geometries that are merged into the complete data set. The function does also take care of locked features not to be edited. The main function is:

- Fill_holes

**Gangsykkel_dissolver.py**

Dissolves *'GangSykkelVeg'* into roads if they are adjacent. The function uses *eliminate_holes* on the *'samferdsel'* layer (without *'GangSykkelVeg'*) afterwards.

**Island_controller.py**

Dissolves areas on small islands that are too small to include multiple land use categories. The category using most of the area of the island will get the area of the other categories. Main function:

- Island_controller

**Overlap_merger.py**

Functionality to merge buffered segments of polygons into the original data set. Main function:

- Create_overlapping_land_use

**Overlap_remover.py**

Removes overlap between geometries to preserve a complete dataset without topological errors. The main function:

- Remove_overlaps

**Passability_layer.py**

Uses the rewritten attribute table from *attribute_changer* to extract geometries with specific values in field *'fremkommelighet'* (*'passability'*). Main function:

- Create_passability_layer

### Parameters

**Parameter_dataclasses.py**

Specifies specific classes for specific functions with initialization parameters. Classes that are defined now:

- EliminateSmallPolygonsParameters
- GangSykkelDissolverParameters
- LandUseParameters
- buff_small_polygon_segments_parameters

**parameters.yml**

Description and parameters for each function that needs elaborated parameters.
