# Arealdekke - Generalization Pipeline

This folder contains all functions and classes that are relevant and specific to the arealdekke / land use generalization pipeline.

#
## 📁 Program Structure

The file structure of our land use pipeline is structured around three core classes: **Arealdekke**, **Category** and **Program History**:

- Arealdekke represents the land use as a whole unit. It is used to handle procedures where relations between the different land use types matter.
- Category represents a single land use type. This is used to process the land use types separately.
- The Program History represents a yaml file that includes information about how far the program got during its last run. This ensures that the program can restart on its last checkpoint if the program suddenly stops.

The Python files is organized into the following folders:

```
root
|___generalization
    |___n10
        |___arealdekke
            |___category_tools
            |___orchestrator
            |___overall_tools
            |___parameters
```

***Category_tools***: Includes functionality used for editing single selections of land use categories.

***Orchestrator***: Contains the core classes and functions that constitutes the skeleton of the pipeline. [*orchestrator.py*](\orchestrator\orchestrator.py) is the pipeline root that initiates and calls all classes.

***Parameters***: Takes care of all parameters used to initialize classes and functionality based upon specific rule sets.

***Overall_tools***: Includes all functionality that handles land use as one unit.

READMEs in the corresponding subfolders will describe functionality in these files further.

#
## 🧰 Instructions

>For information about how to change the minimum and maximum criteria for each category, go to the [readme](parameters/README.md) file within the parameters folder.

**Running the Pipeline**
- *Start:*
    - The pipeline runs from the [orchestrator](orchestrator/orchestrator.py) file located in the orchistrator folder. Ensure that the input_data variable is pointing to the location of the arealdekke data, and that the map_scale is correct. Then, run the file.
- *Stop:*
    - In the case of errors, the pipeline can restart from its last checkpoint. This checkpoint can be a category operation, reinsertion operation, or an arealdekke preprocess operation. The pipeline will not be able to restart from within any of the tools.
    - If it is not desireable to restart, delete the program history yaml file. This ensures that the pipeline begins from scratch next run.
- *End:*
    - The final result can be found within the ag_output folder in ArcGIS Pro under the name: 

**How Edit Categories**
- All arealdekke categories are defined in the [arealdekke_categories_config](orchestrator/arealdekke_categories_config.yml) inside the orchistrator folder. As long the overall structure and variable names stay the same, the categories can be edited however needed. Below is an example of how this structure looks:<br/>
```
  Categories :
    - title : ElvFlate
        operations :
        - buff_small_segments
        - simplify_and_smooth
        accessibility : true
        order: 1
        map_scale: N10

    - title : Innsjo
        operations : 
        accessibility : true
        order: 2
        map_scale: N10

```
- Note that the operations within the categories' operations list must exist within the dictionary returned by the set_cat_tools function in [category class](orchestrator/category_class.py). If there is a spelling mistake, the program will throw an error when the categories are added.

**How Add New Arealdekke Processes**
- *Preprocesseses*
    - All preprocesses must be added to the list returned by the [arealdekke](orchestrator/arealdekke_class.py) ``set_preprocesses`` function. All preprocesses in this list are called consequtively during the arealdekke preprocessing, with index 0 as the first operation called.
    - Since the preprocess operation parameters are hardcoded, remember to create new paths for input or output data in the arealdekke file manager and ensure that the file flows between the operations are correct.
    - If a new preprocess is added to the end of the list, remember to update the ``output_fc`` to match the file path of the output to the last operation. This variable can be found in the arealdekke preprocess function.
    Remember to include ``lambda:`` before the function call. This is to avoid the function being called immediately after the list has been created.
- *Postprocesses*
    - Postprocesses are added the same way as preprocesses, except they are added to the list returned by the [arealdekke](orchestrator/arealdekke_class.py) ``set_postprocesses function``.

**How Add New Operations to Categories**
- All category operations must be added to the dictionary returned by the [category](orchestrator/category_class.py) ``set_cat_tools`` function. Include the name of the tool as a key string and the name as a variable value. Do not include parenthesis, as this will call the function from the dictionary.