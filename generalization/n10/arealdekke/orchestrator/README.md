# Orchestrator

## Class documentation

### 🌻Arealdekke

>[**Arealdekke_categories_config.yml**](Arealdekke_categories_config.yml): Yaml file with setup for each unique land use category with descriptions of how to process the individual land use types. Each category contains:<br/><br/>- <b>Title</b>: category name<br/>- <b>Operations</b>: how the category should be processed<br/>- <b>Accessibility</b>: whether or not the layer is locked / finished processing<br/>- <b>Order</b>: processing rank / order<br/>- <b>Map_scale</b><br><br> The land use class *"Arealdekke"* can be seen [here](arealdekke_class.py).


|**Attributes** | | |
|----------------|-|-|
| **Name** | **Datatype** | **Description** |
| wfm | obj: WorkFileManager | |
| files | dict | Dictionary with all files used in the generalization of land use |
| program_history | [History_class](program_history_class.py) | History_class instance having control of logging and restart of the pipeline |
| preprocessed | bool | Tells if the preprocessing is finished |
| preprocessed_completed | int | Number of completed processes in the main function for preprocessing |
| postprocessed_completed | int | Number of completed processes in the main function for postprocessing |
| map_scale | str | Scale of the map |
| categories | list | List of category objects used in the generalization pipeline for land use |
| final_categories_fc | str | File path to the feature class collecting the final result of process categories |
| final_output_fc | str | File path to the feature class collecting the final result from the entire pipeline |

|**Core** |               |             |                 |                |
|---------|---------------|-------------|-----------------|----------------|
| **Name**| **Parameters** | **Return** | **Description** | **Tools used** |
| init | 
| preprocess | None | None | Performes all the generalization not specific to a category to remove the vast amount of noise in the data set. Sets self.preprocessed = True when finished. |- [*attribute_changer*](..\overall_tools\attribute_changer.py)<br/>- [*create_passability_layer*](..\overall_tools\passability_layer.py)<br/>- [*arealdekke_dissolver*](..\overall_tools\arealdekke_dissolver.py)<br/>- [*island_controller*](..\overall_tools\island_controller.py)<br/>- [*eliminate_small_polygons*](..\overall_tools\eliminate_small_polygons.py)<br/>- [*change_attribute_value_main*](..\overall_tools\small_features_changer.py)<br/>- [*gangsykkel_dissolver*](..\overall_tools\gangsykkel_dissolver.py)|
| add_categories | categories_config_file: Path | None | Adds categories based on what specified in [external yaml file](arealdekke_categories_config.yml).||
| process_categories | None | None | Performes all adjustment needed to generalize each category. Iterate through each category and their specific processing functions specified in the **.yml* file. The function starts by generalizing the specific category for itself, before reinserting the data back into the land use. | - [*remove_overlaps*](..\overall_tools\overlap_remover.py)<br/>- [*fill_holes*](..\overall_tools\fill_holes.py)|
| finish_results | None | None | Post-processes the data by fixing non-dissolved features and mismatch between land use and passability layers. | - [*postprocess_passability_layer*](..\overall_tools\passability_layer.py)<br/>- [*arealdekke_dissolver*](..\overall_tools\arealdekke_dissolver.py) |

|**Getters** |             |            |                 |                |
|------------|-------------|------------|-----------------|----------------|
| **Name**| **Parameters** | **Return** | **Description** | **Tools used** |
| get_map_scale | None | str | Returns the scale of the map. | None |
| get_locked_categories | None | None | Updates the locked_fcs key in the land use file dictionary to include the geometries of all locked features. | None |
| get_category | category title: str | None | Updates the category_fc key in the land use file dictionary to include the geometries of the features with the given category. | None |
| get_arealdekke_data | input_data: str | None | Copies the input data to the main work file during processing of categories. | None |
| get_locked_categories_titles | None | set | Creates a set of locked category names. | None |
| get_num_postprocessors | None | int | Returns the number of functions that are going to be applied during the postprocessing of the land use data. | None |
| __str__ | None | str | ToString-function used for debugging. | None |

|**Setters** |             |            |                 |                |
|------------|-------------|------------|-----------------|----------------|
| **Name**| **Parameters** | **Return** | **Description** | **Tools used** |
| set_preprocesses | None | list | Defines the processes needed to be applied during the preprocessing of the land use data. | None |
| set_postprocesses | None | list | Defines the processes needed to be applied during the postprocessing of the land use data. | None |

##
### 🌻Category

> The Category class *"Category"* can be seen [here](category_class.py).

|**Attributes** | | |
|----------------|-|-|
| **Name**| **Datatype** | **Description** |
| wfm | obj: WorkFileManager | |
| files | dict | Dictionary with files used during generalization of each category. |
| title | str | Name of category |
| operations | list | List of functions that should be applied to this specific category. Order of items determine the order of function execution. Can be empty if no operations should be done. |
| accessibility | bool | Represents if the category can be edited or not. True: open, False: locked. |
| order | int | The order of which the category will be processed in relation to the other land use categories. |
| map_scale | str | The scale of the map the category belongs to. |
| last_processed | str | File path to the last processed version of this category if the processing did begin during the last run. |
| operations_completed | int | Number of operations successfully applied on this category. |
| reinserts_completed | int | Number of operations successfully applied during the process of merging the edited category back into the complete land use data. |



|**Core** |               |             |                 |                |
|---------|---------------|-------------|-----------------|----------------|
| **Name**| **Parameters** | **Return** | **Description** | **Tools used** |
| process_category | - input_fc: Path<br/>- locked_fc: Path<br/>- processed_fc: Path | dict | Iterates through the operations listed in self.operations and generalizes the geometries. Returns a boolean value telling whether or not the category was processed with the pre-defined order of functions.

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
### 🌻Program History

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
| get_history_attribute_cat_lvl | - category_title: str<br/>- key: str | any | Extracts the content of the history file and finds the category specified. Then, it checks if the key belongs to the category and returns the value belonging to the key. | None |
| restore_arealdekke_attributes | None | dict | Extracts contents from history file and checks if the previous run had completed any preprocessing operation steps. If it did, it will return the attributes that belonged to land use last run, excluding the categories. | None |
| restore_arealdekke_categories | None | dict | Extracts contents of history file and checks if the data completed its preprocessing and had begun preprocessing its categories. If both are true, it will collect the informaiton about each category and return them as a list and a boolean. This is then put into a dictionary with "cats_exist", which is a boolean that says if the list was empty or not. | None |
 

|**Setters** |             |            |                 |                |
|------------|-------------|------------|-----------------|----------------|
| **Name**| **Parameters** | **Return** | **Description** | **Tools used** |
| save_history | data: new entry | None | Saves new data to the history file.
| load_history | None | Extracted yaml data | Extracts the data from the yaml history file and returns it to the caller. | None |
| update_history_top_lvl | - key: str<br/>- value: any | None | Updates the value of a specified key that exist in the history file. | None |
| update_history_cat_lvl | - title: str<br/>- key: str<br/>- value: str | None | Updates the value of a specified key that belong to a specific category that exist in the history file. | None |
| new_history_category | - title: str<br/>- operations:list<br/>- accessibility: bool<br/>- order: int<br/>- map_scale: str | None | Adds a new category to the history file. | None
| reset_history | None | None | A new history file is created with the same file path as the path specified during object initialization. | None |

## Additional Notes

- orchestrator
- enum...

