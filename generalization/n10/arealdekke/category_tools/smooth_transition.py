# Libraries

from ast import walk

import arcpy
import numpy as np

from typing import DefaultDict

from composition_configs import core_config
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10

# ========================
# Main function
# ========================


def smooth_transition_between_lines_and_polygons(
    input_fc: str, output_fc: str, line_fc: str
) -> None:
    """
    ...
    """
    working_fc = Arealdekke_N10.smooth_transition__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = file_setup(wfm=wfm)

    clean_lines(line_fc=line_fc, input_fc=input_fc, files=files)
    """
    poly_to_line, line_to_endpoints = connect_polys_and_lines(
        input_fc=input_fc, line_fc=line_fc, files=files
    )

    adjust_polygon_edges(
        input_fc=input_fc,
        poly_to_line=poly_to_line,
        line_to_endpoints=line_to_endpoints,
    )
    """
    arcpy.management.CopyFeatures(in_features=input_fc, out_feature_class=output_fc)

    wfm.delete_created_files()

    print("📐 Smooth transition between lines and polygons completed")


# ========================
# Helper functions
# ========================


def file_setup(wfm: WorkFileManager) -> dict:
    """
    Sets up the file paths for the intermediate files used in the smooth transition process.

    Args:
        wfm (WorkFileManager): An instance of WorkFileManager to generate file paths

    Returns:
        dict: A dictionary containing the absolute paths for intermediate files
    """
    return {
        "intermediate_lines": wfm.build_file_path(
            file_name="intermediate_lines", file_type="gdb"
        ),
        "spatial_join": wfm.build_file_path(file_name="spatial_join", file_type="gdb"),
    }


def clean_lines(line_fc: str, input_fc: str, files: dict) -> None:
    """
    Cleans the lines by erasing the input polygons from the line feature class.

    Args:
        line_fc (str): The path to the line feature class
        input_fc (str): The path to the input polygon feature class
        files (dict): A dictionary containing the absolute paths for intermediate files
    """
    arcpy.management.CopyFeatures(
        in_features=line_fc, out_feature_class=files["intermediate_lines"]
    )
    arcpy.analysis.Erase(
        in_features=files["intermediate_lines"],
        erase_features=input_fc,
        out_feature_class=line_fc,
    )


def connect_polys_and_lines(input_fc: str, line_fc: str, files: dict) -> tuple:
    """
    Connects polygons and lines by performing a spatial join and mapping the relationships.

    Args:
        input_fc (str): The path to the input polygon feature class
        line_fc (str): The path to the line feature class
        files (dict): A dictionary containing the absolute paths for intermediate files

    Returns:
        tuple: A tuple containing poly_to_line and line_to_endpoints dictionaries
    """
    arcpy.analysis.SpatialJoin(
        target_features=input_fc,
        join_features=line_fc,
        out_feature_class=files["spatial_join"],
        join_operation="JOIN_ONE_TO_MANY",
        match_option="INTERSECT",
    )

    poly_to_line = DefaultDict(set)
    with arcpy.da.SearchCursor(
        files["spatial_join"], ["TARGET_FID", "JOIN_FID"]
    ) as cursor:
        for target_fid, join_fid in cursor:
            if join_fid > 0:
                poly_to_line[target_fid].add(join_fid)

    connected_lines = {oid for val in poly_to_line.values() for oid in val}

    line_to_endpoints = {
        oid: {"start": [part[0], part[1]], "end": [part[-2], part[-1]]}
        for oid, geom in arcpy.da.SearchCursor(line_fc, ["OID@", "SHAPE@"])
        if oid in connected_lines
        for part in [geom.getPart(0)]
    }

    return poly_to_line, line_to_endpoints


def adjust_polygon_edges(
    input_fc: str,
    poly_to_line: dict,
    line_to_endpoints: dict,
    window: int = 10,
    spacing: float = 1.0,
    max_shift: float = 10.0,
) -> None:
    """
    Modifies polygon vertices locally around connected line endpoints.

    Args:
        input_fc: Polygon feature class to update
        poly_to_line: Mapping polygon_oid -> set(line_oid)
        line_to_endpoints: Mapping line_oid -> endpoint data
        window: Number of vertices on each side of connection
        spacing: Minimum distance between modified vertices
        max_shift: Maximum funnel deformation distance
    """
    with arcpy.da.UpdateCursor(input_fc, ["OID@", "SHAPE@"]) as cursor:
        for oid, polygon in cursor:
            if oid not in poly_to_line:
                continue

            modified_ring = [pt for pt in polygon.getPart(0) if pt]

            if len(modified_ring) < window * 2 + 1:
                continue

            for line_oid in poly_to_line[oid]:
                line_data = line_to_endpoints.get(line_oid)
                if not line_data:
                    continue

                try:
                    # Detects which of the endpoints this polygon is connected to
                    endpoint_name = match_endpoint(
                        line_data=line_data, polygon_boundary=polygon.boundary()
                    )
                    # Fetches point coordinates for this and closest point
                    endpoint_pt = line_data[endpoint_name][0]
                    # Fetches the direction of the line end
                    line_vec = get_line_vector(line_data=line_data, point=endpoint_name)
                    # Fetches closest point on the polygon
                    idx = find_matching_vertex(ring=modified_ring, endpoint=endpoint_pt)
                    # Fetches the direction of the polygon at that point
                    poly_vec = get_poly_vector(ring=modified_ring, idx=idx)
                    # Estimates the degree of parallelism between the line and polygon at that point
                    strength = calculate_funnel_strength(
                        line_vec=line_vec, poly_vec=poly_vec
                    )
                except Exception as e:
                    raise ValueError(
                        f"Error processing polygon OID {oid} and line OID {line_oid}:\n{e}"
                    )

                if strength < 0.05:
                    # Polygons perpendicular to lines are not modified
                    continue
                
                # Orthogonal vector to the line vector
                line_dir = normalize(line_vec)

                # Fetches indices of vertices to modify, and those to delete
                left_idx, right_idx, indices_to_delete = get_spaced_indices(
                    ring=modified_ring, center_idx=idx, window=window, spacing=spacing
                )
                selected_indices = list(reversed(left_idx)) + [idx] + right_idx
                n_selected = len(selected_indices)

                for pos, pt_idx in enumerate(selected_indices):
                    if pt_idx == idx:
                        continue

                    old_pt = modified_ring[pt_idx]
                    relative_pos = abs(pos - (n_selected - 1) / 2)

                    influence = np.sin(
                        np.pi * (1 - relative_pos / ((n_selected - 1) / 2))
                    )
                    shift = influence * strength * max_shift
                    new_pt = arcpy.Point(
                        old_pt.X + line_dir[0] * shift, old_pt.Y + line_dir[1] * shift
                    )
                    modified_ring[pt_idx] = new_pt

                modified_ring = [
                    pt 
                    for idx, pt in enumerate(modified_ring)
                    if idx not in indices_to_delete
                ]

            array = arcpy.Array(modified_ring)
            new_polygon = arcpy.Polygon(array, polygon.spatialReference)

            cursor.updateRow((oid, new_polygon))


# ========================
# Toolbox
# ========================


def dist(p1, p2):
    return ((p1.X - p2.X) ** 2 + (p1.Y - p2.Y) ** 2) ** 0.5


def normalize(v):
    l = np.hypot(v[0], v[1])
    return (v[0] / l, v[1] / l) if l != 0 else (0, 0)


def match_endpoint(
    line_data: dict, polygon_boundary: arcpy.Polygon, tol: float = 1.0
) -> str:
    start_pt = line_data["start"][0]
    end_pt = line_data["end"][-1]

    if polygon_boundary.distanceTo(start_pt) < tol:
        return "start"
    elif polygon_boundary.distanceTo(end_pt) < tol:
        return "end"
    else:
        raise ValueError("No matching endpoint found within tolerance.")


def get_line_vector(line_data: dict, point: str) -> tuple:
    p0 = line_data[point][0]
    p1 = line_data[point][1]

    return (p1.X - p0.X, p1.Y - p0.Y)


def get_poly_vector(ring: list, idx: int) -> tuple:
    n = len(ring)

    prev_pt = ring[(idx - 1) % n]
    next_pt = ring[(idx + 1) % n]

    return (next_pt.X - prev_pt.X, next_pt.Y - prev_pt.Y)


def get_spaced_indices(
    ring: list, center_idx: int, window: int, spacing: float
)-> tuple[list, list, set]:
    """
    Finds window number of vertices on each side of center_idx,
    where each selected vertex is at least 'spacing' distance
    further along the polygon boundary.

    Returns:
        (left_indices, right_indices, all_visited_indices)
    """
    n = len(ring)

    def walk(step: int):
        selected = []
        current = center_idx
        accumulated = 0.0
        traversed = []

        while len(selected) < window:
            nxt = (current + step) % n
            accumulated += dist(ring[current], ring[nxt])

            current = nxt
            traversed.append(current)
            if accumulated >= spacing:
                selected.append(current)
                accumulated = 0.0
            
            if current == center_idx:
                break
        
        return selected, traversed
    
    
    left_indices, left_traversed = walk(-1)
    right_indices, right_traversed = walk(+1)

    indices_to_delete = (
        set(left_traversed)
        | set(right_traversed)
    ) - (
        set(left_indices)
        | set(right_indices)
        | {center_idx}
    )

    return left_indices, right_indices, indices_to_delete


def simplify_between_selected_vertices(ring: list, selected_indices: list) -> list:
    """
    Keeps only selected vertices in the smoothed area.
    """
    keep = set(selected_indices)
    
    return [
            pt
            for idx, pt in enumerate(ring)
            if idx not in keep or idx in selected_indices
        ]


def calculate_funnel_strength(line_vec: tuple, poly_vec: tuple) -> float:
    """
    0 = perpendicular => min funnel strength
    1 = parallel => max funnel strength
    """
    line_norm = normalize(line_vec)
    poly_norm = normalize(poly_vec)

    dot = np.clip(line_norm[0] * poly_norm[0] + line_norm[1] * poly_norm[1], -1.0, 1.0)

    angle = np.arccos(abs(dot))

    return np.cos(angle)


def find_matching_vertex(ring: list, endpoint: arcpy.Point, tol: float = 1.0) -> int:
    for i, pt in enumerate(ring):
        if dist(pt, endpoint) < tol:
            return i
    raise ValueError("No matching vertex found.")
