import arcpy

from tqdm import tqdm

class Append_Features:
    def __init__(self, workspace: str, output_fc: str):
        """
        Initializes a new Append Feature instance.

        Args:
            workspace (str): Filepath to the gdb file where the feature classes are stored
            output_fc (str): Filepath to the new feature class that should contain the unified data
        """
        self.workspace = workspace
        self.output_fc = output_fc

    def append_features(self, file_name_structure: str):
        """
        Creates one single feature class containing all the data.

        Copys the first feature class before it iterates through
        the rest of the folder and appends the remaining data.

        Args:
            file_name_structure (str): The file name structure that the feature classes to append should follow
        """
        arcpy.env.workspace = self.workspace

        fcs = arcpy.ListFeatureClasses(file_name_structure)

        if not fcs:
            raise ValueError(f"None feature classes were found in '{self.workspace}' following the structure {file_name_structure}.")
        
        print(f"Combines {len(fcs)} feature classes...")

        if arcpy.Exists(self.output_fc):
            arcpy.management.Delete(self.output_fc)

        arcpy.management.CopyFeatures(fcs[0], self.output_fc)

        for fc in tqdm(fcs[1:], desc="Appends fcs", colour="yellow", leave=False):
            arcpy.management.Append(fc, self.output_fc, "NO_TEST")
        
        print(f"Finished! Combined {len(fcs)} feature classes.")
