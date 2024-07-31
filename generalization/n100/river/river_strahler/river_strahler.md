# River Direction

## Setup

### Configuring paths
Create a config.py file and add the paths similar to config_template.py

## Requirements

- Python 3.x
- ArcPy (part of ArcGIS)
- GeoPandas
- Shapely
- NetworkX
- Matplotlib

# Script Descriptions

## Main scripts

### strahler_hierarchy.py

This script calculates Strahler values for river segments using a directed graph approach. It processes river data either from a shapefile or from feature classes in a geodatabase, and outputs the Strahler values for each river segment.

### process_river_basins_direction.py

This script processes river segments within specified drainage basins, calculates height values, and identifies segments that need to be flipped to ensure correct flow direction. The final output is a merged shapefile containing flipped river segments if necessary.

## Intermediate scripts

### join_river_and_drainage_basin.py
Sets workspace and input paths, creates feature layers for rivers and drainage basins, selects a specified drainage basin, finds and selects rivers within it, and saves the selected rivers to a new shapefile.

### join_river_and_height_data.py
Extracts vertices from the combined river and drainage basin shapefile to points, extracts height values from a raster file to the points, reconstructs 3D river lines with the extracted height values, and saves the 3D river lines to a new shapefile.

### build_river_network.py
Reads the 3D river lines shapefile, builds an undirected graph of rivers using NetworkX, adds nodes and edges based on river start and end points with elevation differences determining the flow direction, and visualizes the river network using Matplotlib.