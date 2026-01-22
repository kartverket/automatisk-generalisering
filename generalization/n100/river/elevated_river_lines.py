import arcpy
import os

from custom_tools.decorators.timing_decorator import timing_decorator
from env_setup import environment_setup
from file_manager.n100.file_manager_rivers import River_N100
import generalization.n100.river.config as config


class RiverElevator:
    def __init__(self, input_lines_fc: str, output_fc: str):
        """
        Class for enriching river polyline features with elevation sampled from raster TIFF files containing height data.

        Args:
            input_lines_fc (str): input feature class path
            output_fc (str): output feature class path
        """
        environment_setup.main()
        self.input_lines_fc = input_lines_fc
        self.output_fc = output_fc
        self.tif_folder = config.tif_folder
        self.rasters = []
        self.sr = arcpy.Describe(self.input_lines_fc).spatialReference

    @timing_decorator
    def load_rasters(self):
        """
        Load all TIFF raster files from the configured folder into memory.
        """
        for f in os.listdir(self.tif_folder):
            if f.lower().endswith(".tif"):
                self.rasters.append(arcpy.Raster(os.path.join(self.tif_folder, f)))

    @timing_decorator
    def create_output_fc(self):
        """
        Create the output feature class with Z-enabled polyline geometry.
        """
        arcpy.CreateFeatureclass_management(
            os.path.dirname(self.output_fc),
            os.path.basename(self.output_fc),
            "POLYLINE",
            has_z="ENABLED",
            spatial_reference=self.sr,
        )

        input_fields = arcpy.ListFields(self.input_lines_fc)
        for fld in input_fields:
            if fld.type not in ("OID", "Geometry"):
                arcpy.AddField_management(
                    self.output_fc,
                    fld.name,
                    fld.type,
                    fld.precision,
                    fld.scale,
                    fld.length,
                )

    def sample_z(self, pt: arcpy.Point):
        """
        Sample the elevation for a given point from loaded rasters.

        Args:
            pt (arcpy.Point): The point geometry to sample
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
        return None

    @timing_decorator
    def build_3d_lines(self):
        """
        Construct new 3D polylines by sampling Z-values for each vertex.
        """
        input_fields = arcpy.ListFields(self.input_lines_fc)
        in_fields = [f.name for f in input_fields if f.type not in ("OID", "Geometry")]
        out_fields = in_fields + ["SHAPE@"]

        with arcpy.da.SearchCursor(
            self.input_lines_fc,
            in_fields + ["SHAPE@"],
        ) as cur, arcpy.da.InsertCursor(self.output_fc, out_fields) as icur:

            for row in cur:
                attrs = row[:-1]
                geom = row[-1]

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

    @timing_decorator
    def run(self):
        """
        Run the process to enrich river polyline features with elevation.
        """
        self.load_rasters()
        self.create_output_fc()
        self.build_3d_lines()


if __name__ == "__main__":
    input_lines_fc = River_N100.river_strahler___output___n100.value
    output_fc = River_N100.river_elevated___output___n100.value

    RiverElevator(input_lines_fc, output_fc).run()
