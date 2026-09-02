"""TEMPLATE — not shipped. Target package: `src/ag/core/`.

Pure: no arcpy, no clients, no filesystem, no Kubernetes. Imports stdlib only.
Everything here is evaluated at import time to build the graph, so nothing in it may
read data or invoke a geoprocessing engine (02-runtime §2.6).
"""
