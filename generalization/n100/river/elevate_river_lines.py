import arcpy
import os
import statistics

from custom_tools.decorators.timing_decorator import timing_decorator
from env_setup import environment_setup
import generalization.n100.river.config as config


class RiverElevator:
    """
    Class for enriching river polyline features with elevation sampled from raster TIFF
    files containing height data.
    """

    def __init__(self, input_lines_fc: str, output_fc: str):
        """
        Creates an instance of RiverElevator.
        """
        environment_setup.main()

        self.input_lines_fc = input_lines_fc
        self.output_fc = output_fc
        self.tif_folder = config.tif_folder
        self.rasters = []
        self.sr = arcpy.Describe(self.input_lines_fc).spatialReference

    def load_rasters(self) -> None:
        """
        Load all TIFF raster files from the configured folder into memory.
        """
        for f in os.listdir(self.tif_folder):
            if f.lower().endswith(".tif"):
                self.rasters.append(arcpy.Raster(os.path.join(self.tif_folder, f)))

    def create_output_fc(self) -> None:
        """
        Create the output feature class with Z-enabled polyline geometry.
        """
        if arcpy.Exists(self.output_fc):
            arcpy.management.Delete(self.output_fc)

        arcpy.management.CreateFeatureclass(
            os.path.dirname(self.output_fc),
            os.path.basename(self.output_fc),
            "POLYLINE",
            has_z="ENABLED",
            spatial_reference=self.sr,
        )

        input_fields = arcpy.ListFields(self.input_lines_fc)
        for fld in input_fields:
            if fld.type not in ("OID", "Geometry"):
                arcpy.management.AddField(
                    self.output_fc,
                    fld.name,
                    fld.type,
                    fld.precision,
                    fld.scale,
                    fld.length,
                )

    def sample_z(self, pt: arcpy.Point) -> float:
        """
        Sample the elevation for a given point from loaded rasters.
        """
        for r in self.rasters:
            if r.extent.contains(pt):
                col = int((pt.X - r.extent.XMin) / r.meanCellWidth)
                row = int((r.extent.YMax - pt.Y) / r.meanCellHeight)

                if 0 <= row < r.height and 0 <= col < r.width:
                    arr = arcpy.RasterToNumPyArray(
                        r,
                        lower_left_corner=arcpy.Point(pt.X, pt.Y),
                        ncols=1,
                        nrows=1,
                    )
                    return float(arr[0, 0])

    def build_3d_lines(self) -> None:
        """
        Construct new 3D polylines by sampling Z-values for each vertex.
        """
        in_fields = [
            f.name
            for f in arcpy.ListFields(self.input_lines_fc)
            if f.type not in ("OID", "Geometry")
        ]
        out_fields = in_fields + ["SHAPE@"]

        with arcpy.da.SearchCursor(
            self.input_lines_fc,
            in_fields + ["SHAPE@"],
        ) as cur, arcpy.da.InsertCursor(self.output_fc, out_fields) as icur:

            for row in cur:
                attrs = row[:-1]
                geom = row[-1]

                if geom is None:
                    continue

                new_parts = []
                for part in geom:
                    new_pts = []
                    for pt in part:
                        if pt is None:
                            new_pts.append(None)
                            continue

                        z = self.sample_z(pt)
                        if z is None:
                            z = 0.0

                        new_pts.append(arcpy.Point(pt.X, pt.Y, z))

                    new_parts.append(new_pts)

                new_geom = arcpy.Polyline(arcpy.Array(new_parts), self.sr, has_z=True)
                icur.insertRow(list(attrs) + [new_geom])

    def add_mean_z(self) -> None:
        """
        Add meanZ to the feature class.
        """
        fields = [f.name for f in arcpy.ListFields(self.output_fc)]
        if "meanZ" not in fields:
            arcpy.management.AddField(self.output_fc, "meanZ", "DOUBLE")

        with arcpy.da.UpdateCursor(self.output_fc, ["SHAPE@", "meanZ"]) as cur:
            for geom, meanz in cur:

                zvals = []

                if geom is None:
                    continue
                for part in geom:
                    for pt in part:
                        if pt:
                            zvals.append(pt.Z)

                if not zvals:
                    cur.updateRow([geom, None])
                    continue

                meanz = statistics.mean(zvals)

                cur.updateRow([geom, meanz])

    @timing_decorator
    def run(self) -> None:
        """
        Run the process to enrich river polyline features with elevation.
        """
        self.load_rasters()
        self.create_output_fc()
        self.build_3d_lines()
        self.add_mean_z()
