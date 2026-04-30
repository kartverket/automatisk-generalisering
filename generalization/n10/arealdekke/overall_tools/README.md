# Overall_tools


### Attributes

| Module Name       | Parameters | Return | File path | Description         |
|-------------------|------------|--------|-----------|---------------------|
|[**attribute_analyzer**](attribute_analyzer.py) | **** | **** | attribute_analyzer.py | File analyzing attribute data from csv file and lists. Core processes: <br/>- Sort_results <br/>- Write_to_file <br/>- Load_rules |
|[**attribute_changer**](attribute_changer.py) | input_fc: str,<br/>output_fc: str | None | attribute_changer.py | Re-categorizes *'arealdekke'* based on the fields: *"Arealdekke", "Hovedklasse", "Underklasse", "Grunnforhold"*. Overwrites the original *"arealdekke"* field to replace it with two new fields: *"gammel_arealdekke"* and *"fremkommelighet"*.

##
> [**Attribute_prioritizing.csv**](attribute_prioritizing.csv) is a CSV file that outlines how the arealdekke categories must be sorted and reclassified. Can be imported into other files as a dictionary. The file contains the following columns: <br/>- Arealdekke <br/>- Hovedklasse <br/>- Underklasse <br/>- Grunnforhold <br/>- Ny_arealdekke <br/>- Fremkommelighet

##
### Elimination and Dissolving


| Module Name       | Parameters | Return | File path | Description         |
|-------------------|------------|--------|-----------|---------------------|
|[**partition_call**](arealdekke_dissolver.py)| input_fc: str,<br/>output_fc: str,<br/>map_scale: str | None | arealdekke_dissolver.py | Main dissolve class that dissolves based on the categories defined in *attribute_changer.py*. This file contains: <br/> - **Restore_data_polygon_without_feature_to_point**. This function follows the rules for restoring data after dissolving and can be used by other functions / classes.|
| [**partition_call**](eliminate_small_polygons.py)| input_fc: str,<br/>output_fc: str,<br/>map_scale: str | None | eliminate_small_polygons.py| Eliminates small polygons based on *area times isoperimetric quotient* and removes narrow polygon parts with a minus buffer.|
|[**eliminate_holes**](eliminate_small_polygons.py)| input_fc: str,<br/>output_fc: str,<br/>selection: str,<br/>wfm: WorkFileManager | None | eliminate_small_polygons.py| Function in eliminate_small_polygons. Finds and eliminates holes in selected polygons based on criteria specified in parameters.yml.|
|[**fill_holes**](fill_holes.py)| input_fc: str,<br/>output_fc: str,<br/>target:str,<br/>locked_categories: set | None | fill_holes.py| Functionality to remove holes and replace it with surrounding geometries that are merged back into the complete data set. The function does also take care of locked features not to be edited.|
|[**partition_call**](gangsykkel_dissolver.py)| input: str,<br/>output: str,<br/>map_scale: str | None | Gangsykkel_dissolver.py | Dissolves *'GangSykkelVeg'* into roads if they are adjacent. Uses *eliminate_holes* on the *'samferdsel'* layer (without *'GangSykkelVeg'*) afterwards.|
|[**island_controller**](island_controller.py)| input: str,<br/>output: str | None | Island_controller.py | Dissolves areas on small islands that are too small to include multiple land use categories. The category using most of the area of the island will get the area of the other categories.|

### Reinsertion

| Module Name       | Parameters | Return | File path | Description         |
|-------------------|------------|--------|-----------|---------------------|
|[**overlap_merger**](overlap_merger.py)| input_fc: str,<br/>buffered_fc: str,<br/>ouput_fc:str | None |Overlap_merger.py | Merges buffered segments of polygons into the original data set. Main function is called Create_overlapping_land_use.|
|[**overlap_remover**](overlap_remover.py)| input_fc: str,<br/>buffered_fc: str,<br/>locked_fc: str<br/>ouput_fc: str,<br/>changed_area:str<br/> | None | Overlap_remover.py | Removes overlap between geometries to preserve a complete dataset without topological errors. The main function called Remove_overlaps.|


### Passability

| Module Name       | Parameters | Return | File path | Description         |
|-------------------|------------|--------|-----------|---------------------|
|[**passability_layer**](passability_layer.py)| input_fc: str,<br/>output_fc: str | None | Passability_layer.py | Uses the rewritten attribute table from *attribute_changer* to extract geometries with specific values in field *'fremkommelighet'* (*'passability'*). Main function called Create_passability_layer. |