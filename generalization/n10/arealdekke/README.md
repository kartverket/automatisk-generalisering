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

>**Arealdekke_categories_config.yml**. Yaml file with setup for each unique land use category with descriptions of how to process the individual land use types. Each category contains:<br/>- Title (category name)<br/>- Operations (how the category should be processed)<br/>- Accessibility (whether or not the layer is locked / finished processing)<br/>- Order (processing rank / order)<br/>- Map_scale


|**Attributes** | | |
|----------------|-|-|
| **Name**| **Datatype** | **Description** |
| wfm | obj: WorkFileManager ||
| files | dict | Dictionary with all files used in the generalization of land use. |
| preprocessed | bool | Tells if the preprocessing is finished. |
| __map_scale | str | Scale of the map. |

|**Core** |               |             |                 |                |
|---------|---------------|-------------|-----------------|----------------|
| **Name**| **Parameters** | **Return** | **Description** | **Tools used** |
| init | 
| preprocess | None | None | Performes all the generalization not specific to a category to remove the vast amount of noise in the data set. Sets self.preprocessed = True when finished. |-*Attribute_changer*<br/>- *Create_passability_layer*<br/>- *Arealdekke_dissolver*<br/>- *Island_controller*<br/>- *Eliminate_small_polygons*<br/>- *Gangsykkel_dissolver*|
| add_categories | None | None | Adds categories based on what specified in external yaml file (*arealdekke_categories_config.yml*).||
| process_categories | None | None | Performes all adjustment needed to generalize each category. Iterate through each category and their specific processing functions specified in the **.yml* file. The function starts by generalizing the specific category for itself, before the reinserting it back into the arealdekke. | -*remove_overlaps*<br/>-*fill_holes*|

|**Getters** |             |            |                 |                |
|------------|-------------|------------|-----------------|----------------|
| **Name**| **Parameters** | **Return** | **Description** | **Tools used** |
| get_map_scale | None | str | Returns the scale of the map. | None |
| get_locked_categories | None | None | Updates the locked_fcs key in the arealdekke files dictionary to include the feature classes of all locked files | * |
| get_category | category title: str | 

|**Setters** |             |            |                 |                |
|------------|-------------|------------|-----------------|----------------|
| **Name**| **Parameters** | **Return** | **Description** | **Tools used** |


##
### 🌻Category_class.py

|**Attributes** | | |
|----------------|-|-|
| **Name**| **Datatype** | **Description** |
| title | str | Name of category |
| operations | list | List of functions that should be applied to this specific category. Order of items determine the order of function execution. Can be empty if no operations should be done. |
| accessibility | bool | Represents if the category can be edited or not. True: open, False: locked. |
| order | int | The order of which the category will be processed in relation to the other arealdekke categories. |
| map_scale | str | The scale of the map the category belongs to. |
| wfm | obj: WorkFileManager | |
| files | dict | Dictionary with files used during generalization of each category. |


|**Core** |               |             |                 |                |
|---------|---------------|-------------|-----------------|----------------|
| **Name**| **Parameters** | **Return** | **Description** | **Tools used** |
| process_category | input_fc: Path, locked_fc: Path, processed_fc: Path | dict | Iterates through the operations listed in self.operations and generalizes the geometries. Returns the 

|**Getters** |             |            |                 |                |
|------------|-------------|------------|-----------------|----------------|
| **Name**| **Parameters** | **Return** | **Description** | **Tools used** |
| get_title | None | str | Returns the title of the category. | None |
| get_order | None | int | Returns the order of the category. | None |
| get_accessibility | None | bool | Returns True or False based on if the category is open or locked. | None |
| get_map_scale | None | str | Returns the map scale the category generalization must be based on. | None |
| __str___ | None | str | Returns a string with most of the category attributes. Used for debugging etc. | None |


|**Setters** |             |            |                 |                |
|------------|-------------|------------|-----------------|----------------|
| **Name**| **Parameters** | **Return** | **Description** | **Tools used** |
| set_accessibility | bool | None | Locks or opens the category. | None |

##
### 🌻Program_history_class.py

|**Attributes** | | |
|----------------|-|-|
| **Name**| **Datatype** | **Description** |
| program_history_path | obj: Path | File path to the yaml file where everything is tracked. |
| new_history_created | bool | Tells if the history previously existed, or if the file had to be created from scratch. |


|**Core** |               |             |                 |                |
|---------|---------------|-------------|-----------------|----------------|
| **Name**| **Parameters** | **Return** | **Description** | **Tools used** |
| init | file path: Path | None | Initialises the object by checking if the file path sent is empty or not. If it is empty, a new file will be created with the same file name. | None |

|**Getters** |             |            |                 |                |
|------------|-------------|------------|-----------------|----------------|
| **Name**| **Parameters** | **Return** | **Description** | **Tools used** |
| get_new_history_created | None | bool | Returns True or False depending on if a new history file was created. | None |
| get_history_attribute_top_lvl | key: str | any | Extracts the content of the history file and checks if there is a key that is spelled the same as the key parameter sent to the function. If found, it returns the value belonging to the key. | None |
| get_history_attribute_cat_lvl | category_title: str<br/>key: str | any | Extracts the content of the history file and finds the category specified. Then, it checks if the key belongs to the category and returns the value belonging to the key. | None |
| restore_arealdekke_attributes | None | dict | Extracts contents of history file and checks if the previous run had completed any preprocessing operation steps. If it did, it will return the attributes that belonged to arealdekke last run, excluding the categories. | None |
| restore_arealdekke_categories | None | dict | Extracts contents of history file and checks if the data completed its preprocessing and had begun preprocessing its categories. If both are true, it will collect the informaiton about each category and return them as a list and a boolean. This is then put into a dictionary with "cats_exist", which is a boolean that says if the list was empty or not. | None |
 

|**Setters** |             |            |                 |                |
|------------|-------------|------------|-----------------|----------------|
| **Name**| **Parameters** | **Return** | **Description** | **Tools used** |
| save_history | data: new entry | None | Saves new data to the history file.
| load_history | None | Extracted yaml data | Extracts the data from the yaml history file and returns it to the caller. | None |
| update_history_top_lvl | key: str<br/>value: any | None | Updates the value of a specified key that exist in the history file. | None |
| update_history_cat_lvl | title: str<br/>key: str<br/>value: str | None | Updates the value of a specified key that belong to a specific category that exist in the history file. | None |
| new_history_category | title: str<br/>operations:list<br/>accessibility: bool<br/>order: int<br/>map_scale: str<br/> | None | Adds a new category to the history file. | None
| reset_history | None | None | A new history file is created with the same file path as the path specified during object initialisation. | None |

##
## 🧩 Category Tools

> Input for all category tools: <br/> input_fc

| Module Name       | File path         | Description                   |
|-------------------|-------------------|-------------------------------|
| **buff_small_polygon_segments** | buff_small_polygon_segments.py | Buffs polygon segments under a minimum width requirement without overlapping locked features. *Create_overlapping_land_use* can be used afterwards to merge the buffered segments back into the layer. |
|**simplify_land_use**| Simplify_land_use.py | Uses simplify and smooth to adjust polygons and remove small, extra details.|



##
## 🧩 Overall_tools


### Attributes

| Module Name       | Parameters | Return | File path | Description         |
|-------------------|------------|--------|-----------|---------------------|
|**** | Attribute_analyzer.py | File analyzing attribute data from csv file and list. Core processes: <br/>- Sort_results <br/>- Write_to_file <br/>- Load_rules |
|**attribute_changer** | attribute_changer.py | Re-categorizes *'arealdekke'* based on the fields: *"Arealdekke", "Hovedklasse", "Underklasse", "Grunnforhold"*. Overwrites the original *"Arealdekke"* field to replace it with two new fields: *"gammel_arealdekke"* and *"fremkommelighet"*.

##
> **Attribute_prioritizing.csv** is a CSV file that outlines how the arealdekke categories must be sorted and reclassified. Can be imported into other files as a dictionary. The file contains the following columns: <br/>- Arealdekke <br/>- Hovedklasse <br/>- Underklasse <br/>- Grunnforhold <br/>- Ny_arealdekke <br/>- Fremkommelighet
##
### Elimination and Dissolving


| Module Name       | Parameters | Return | File path | Description         |
|-------------------|------------|--------|-----------|---------------------|
|**partition_call**| arealdekke_dissolver.py | Main dissolve class that dissolves based on the categories defined in           *attribute_changer.py*. This file contains: <br/> - **Restore_data_polygon_without_feature_to_point**. This function follows the rules for restoring data after dissolving and can be used by other functions / classes.|
| **partition_call**| Eliminate_small_polygons.py| Eliminates small polygons based on *area times isoperimetric quotient* and removes narrow polygon parts with a minus buffer.|
|**eliminate_holes**| Eliminate_small_polygons| Function in Eliminate_small_polygons. Finds and eliminates holes in selected polygons based on criteria spesified in parameters.yml.|
|**fill_holes**| Fill_holes.py| Functionality to remove holes and replace it with geometries that are merged into the complete data set. The function does also take care of locked features not to be edited.|
|**partition_call**| Gangsykkel_dissolver.py | Dissolves *'GangSykkelVeg'* into roads if they are adjacent. Uses *eliminate_holes* on the *'samferdsel'* layer (without *'GangSykkelVeg'*) afterwards.|
|**island_controller**| Island_controller.py | Dissolves areas on small islands that are too small to include multiple land use categories. The category using most of the area of the island will get the area of the other categories.|

### Reinsertion

| Module Name       | Parameters | Return | File path | Description         |
|-------------------|------------|--------|-----------|---------------------|
|**overlap_merger**| Overlap_merger.py | Merges buffered segments of polygons into the original data set. Main function is called Create_overlapping_land_use.|
|**overlap_remover**| Overlap_remover.py | Removes overlap between geometries to preserve a complete dataset without topological errors. The main function called Remove_overlaps.|


### Passability

| Module Name       | Parameters | Return | File path | Description         |
|-------------------|------------|--------|-----------|---------------------|
|**passability_layer**| Passability_layer.py | Uses the rewritten attribute table from *attribute_changer* to extract geometries with specific values in field *'fremkommelighet'* (*'passability'*). Main function called Create_passability_layer. |


##
## 🗨️🦜 Parameters

**Parameter_dataclasses.py**. Specifies classes for functions with initialization parameters. Classes that are defined now:

- EliminateSmallPolygonsParameters
- GangSykkelDissolverParameters
- LandUseParameters
- buff_small_polygon_segments_parameters

**parameters.yml**. Description and parameters for each function that needs elaborated parameters.
