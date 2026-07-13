# 🧩 Category Tools

> <u>Input for all category tools:</u> <br/> <br/> <b>target (str):</b> The land use type of the segments to be buffered <br/> <b>input_fc (str):</b> The feature class containing the original data with type 'target' <br/> <b>output_fc (str):</b> The feature class to store the buffered data <br/> <b>locked_fc (set):</b> A set of feature classes representing locked areas <br/> <b>map_scale (str):</b> The map scale for the operation <br/> <b> allowed (list): </b> A list of allowed / available land use types to consider <br/> <b> boundary (str): </b> Feature type used as boundary for the process <br/> <b> track_type (str): </b> Land use type of thin tracks through polygons that should be removed <br/> <br/> Not everyone are required, but all tools must match these 5 inputs.

| Module Name       | File path         | Description                   |
|-------------------|-------------------|-------------------------------|
| **aggregate_category** | [area_aggregator.py](area_aggregator.py) | Aggregation function used to combine smaller objects of a specific type into larger polygons by changing the land use type of surrounding features. |
| **buff_small_polygon_segments** | [buff_small_polygon_segments.py](buff_small_polygon_segments.py) | Buffs polygon segments under a minimum width requirement without overlapping locked features. *Create_overlapping_land_use* can be used afterwards to merge the buffered segments back into the layer. |
| **remove_thin_tracks** | [remove_thin_tracks.py](remove_thin_tracks.py) | Changes the land use type for track type that are too thin to go through the target type to the target type. |
|**simplify_and_smooth_polygon**| [simplify_polygon.py](simplify_polygon.py) | Uses simplify and smooth to adjust polygons and remove small, extra details.|
| **pointify_thin_poly** | [thin_poly_to_point.py](thin_poly_to_point.py) | Detects thin areas of the land use type target and changes this to the type of the largest adjacent area. The changed area is also replaced with a line of points going along the centre line of the deleted area |
