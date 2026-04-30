# 🧩 Category Tools

> <u>Input for all category tools:</u> <br/> <br/> <b>target (str):</b> The land use type of the segments to be buffered <br> <b>input_fc (str):</b> The feature class containing the original data with type 'target' <br> <b>output_fc (str):</b> The feature class to store the buffered data <br> <b>locked_fc (set):</b> A set of feature classes representing locked areas <br> <b>map_scale (str):</b> The map scale for the operation <br> <br/> Not everyone are required, but all tools must match these 5 inputs.

| Module Name       | File path         | Description                   |
|-------------------|-------------------|-------------------------------|
| **buff_small_polygon_segments** | [buff_small_polygon_segments.py](buff_small_polygon_segments.py) | Buffs polygon segments under a minimum width requirement without overlapping locked features. *Create_overlapping_land_use* can be used afterwards to merge the buffered segments back into the layer. |
|**simplify_and_smooth_polygon**| [simplify_polygon.py](simplify_polygon.py) | Uses simplify and smooth to adjust polygons and remove small, extra details.|
