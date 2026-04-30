# Imports
import arcpy
from custom_tools.decorators.timing_decorator import timing_decorator

from composition_configs import core_config
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n10.file_manager_facilities import Facility_N10
from input_data import input_n10

arcpy.env.overwriteOutput = True


def main():

    environment_setup.main()

    working_fc = Facility_N10.train_station__n10_facility.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)
    fetch_data(files=files)

    find_track_rotation(files=files)


@timing_decorator
def create_wfm_gdbs(wfm: WorkFileManager) -> dict:

    train_track = wfm.build_file_path(file_name="train_tracks", file_type="gdb")
    train_station = wfm.build_file_path(file_name="train_station", file_type="gdb")
    train_station_snapped = wfm.build_file_path(
        file_name="train_station_snapped", file_type="gdb"
    )
    train_station_buffer = wfm.build_file_path(
        file_name="train_station_buffer", file_type="gdb"
    )
    track_segment_multi = wfm.build_file_path(
        file_name="track_segment_multi", file_type="gdb"
    )
    track_segment_single = wfm.build_file_path(
        file_name="track_segment_single", file_type="gdb"
    )
    train_station_rotated = wfm.build_file_path(
        file_name="train_station_rotated", file_type="gdb"
    )

    return {
        "train_track": train_track,
        "train_station": train_station,
        "train_station_snapped": train_station_snapped,
        "train_station_buffer": train_station_buffer,
        "track_segment_multi": track_segment_multi,
        "track_segment_single": track_segment_single,
        "train_station_rotated": train_station_rotated,
    }


@timing_decorator
def fetch_data(files: dict) -> None:
    arcpy.management.CopyFeatures(
        in_features=input_n10.bane, out_feature_class=files["train_track"]
    )
    arcpy.management.CopyFeatures(
        in_features=input_n10.jernbanestasjon, out_feature_class=files["train_station"]
    )
    arcpy.management.CopyFeatures(
        in_features=input_n10.jernbanestasjon,
        out_feature_class=files["train_station_snapped"],
    )


@timing_decorator
def find_track_rotation(files: dict) -> None:
    arcpy.edit.Snap(
        files["train_station_snapped"], [[files["train_track"], "EDGE", "40 Meters"]]
    )
    arcpy.analysis.Buffer(
        files["train_station_snapped"],
        files["train_station_buffer"],
        "5 Meters",
        "FULL",
    )

    tracks_under_station = arcpy.management.SelectLayerByLocation(
        files["train_track"],
        "INTERSECT",
        files["train_station_snapped"],
        None,
        "NEW_SELECTION",
    )
    tracks_under_station_layer = arcpy.management.MakeFeatureLayer(
        tracks_under_station, "tracks_under_station_layer"
    )

    arcpy.analysis.Clip(
        tracks_under_station_layer,
        files["train_station_buffer"],
        files["track_segment_multi"],
    )
    arcpy.management.MultipartToSinglepart(
        files["track_segment_multi"], files["track_segment_single"]
    )
    arcpy.management.CalculateGeometryAttributes(
        files["track_segment_single"], [["LINE_BEARING", "LINE_BEARING"]]
    )

    arcpy.analysis.SpatialJoin(
        files["train_station_snapped"],
        files["track_segment_single"],
        files["train_station_rotated"],
        "JOIN_ONE_TO_ONE",
        "KEEP_ALL",
        None,
        "INTERSECT",
    )

    new_field_name = "ROTASJON"
    arcpy.management.AddField(files["train_station"], new_field_name)

    with arcpy.da.UpdateCursor(
        files["train_station"], ["OBJECTID", new_field_name]
    ) as original_cursor:
        for original_station in original_cursor:

            with arcpy.da.SearchCursor(
                files["train_station_rotated"], ["OBJECTID", "LINE_BEARING"]
            ) as copy_cursor:
                for copy_station in copy_cursor:

                    if original_station[0] == copy_station[0]:
                        original_station[1] = copy_station[1]
                        original_cursor.updateRow(original_station)
                        break


if __name__ == "__main__":
    main()
