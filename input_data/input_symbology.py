# Libraries

from config import input_data_folder

from pathlib import Path

# Setup main symbology path

symbology_path = Path.joinpath(Path(input_data_folder), "symbology")

# Getter function for symbology paths corresponding to map scale


def get_symbology_paths(map_scale: str) -> dict:
    map_scale = map_scale.lower()
    symbology_scale_folder = Path.joinpath(symbology_path, map_scale)

    symbologies = {}

    for key, val in DATA.get(map_scale, {}).items():
        symbologies[key] = Path.joinpath(symbology_scale_folder, val)

    return symbologies


# Create dataset for imports

DATA = {
    "n100": {
        "begrensnings_kurve_buffer": "begrensningskurve_buffer_water_features_n100.lyrx",
        "begrensnings_kurve_line": "N100_Arealdekke_grense_blå_maske.lyrx",
        "bygning_areal": "grunnriss_symbology_n100.lyrx",
        "bygningspunkt": "building_points_symbology_n100.lyrx",
        "jernbane": "railway_buffer.lyrx",
        "jernbanestasjon": "jernbanestasjon_square.lyrx",
        "samferdsel": "M616_Samferdsel.lyrx",
        "vei_buffer": "building_polygons_drawn_from_points.lyrx",
    },
    "n250": {
        "begrensnings_kurve_line": "N250_Begrensningskurve.lyrx",
        "samferdsel": "N250_Samferdsel.lyrx",
    },
}
